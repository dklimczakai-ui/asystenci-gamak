"""
Crypto Trading Scanner — główny skrypt
Pobiera OHLCV z Gate.io (publiczne, bez klucza), analizuje setupy A/B/C/D,
filtruje po BTC regime, wysyła alerty na Telegram.

Użycie:
    python scanner.py             # run once
    python scanner.py --loop      # loop co 15 min
    python scanner.py --test BTC  # test pojedynczego aktywum
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import pandas as pd

import config
from indicators import atr
from notifier import send_alert, send_text
from setups import SETUP_FUNCTIONS
from sizer import risk_summary


# ──────────────────────────────────────────────
# EXCHANGE CLIENT
# ──────────────────────────────────────────────
def get_exchange():
    ex_class = getattr(ccxt, config.EXCHANGE_ID)
    ex = ex_class({"enableRateLimit": True, "options": {"defaultType": config.EXCHANGE_DEFAULT_TYPE}})
    return ex


def fetch_ohlcv(ex, symbol: str, tf: str, limit: int = 300) -> pd.DataFrame:
    try:
        data = ex.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
        df = pd.DataFrame(data, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        return df
    except Exception as e:
        log(f"ERROR fetching {symbol} {tf}: {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────
# BTC REGIME FILTER
# ──────────────────────────────────────────────
def btc_regime(ex) -> dict:
    df = fetch_ohlcv(ex, "BTC/USDT:USDT", "1d", limit=10)
    if df.empty:
        return {"ok": False}
    last = df.iloc[-1]
    prev = df.iloc[-2]
    change_24h = (last["close"] - prev["close"]) / prev["close"] * 100
    ma200 = df["close"].rolling(200).mean().iloc[-1] if len(df) >= 200 else None
    return {
        "ok": True,
        "close": float(last["close"]),
        "change_24h": round(change_24h, 2),
        "risk_off": change_24h < -config.BTC_REGIME_DROP_THRESHOLD,
        "above_ma200": bool(ma200 and last["close"] > ma200),
    }


# ──────────────────────────────────────────────
# COOLDOWN (anti-spam)
# ──────────────────────────────────────────────
def load_cooldown() -> dict:
    if config.COOLDOWN_FILE.exists():
        return json.loads(config.COOLDOWN_FILE.read_text())
    return {}


def save_cooldown(data: dict) -> None:
    config.COOLDOWN_FILE.write_text(json.dumps(data, indent=2))


def in_cooldown(key: str, cooldowns: dict) -> bool:
    last = cooldowns.get(key, 0)
    return (time.time() - last) < (config.COOLDOWN_MINUTES * 60)


# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────
def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    # Na Lambdzie CloudWatch zbiera stdout — nie zapisujemy do plików
    if getattr(config, "IS_LAMBDA", False):
        return
    try:
        log_file = config.LOGS_DIR / f"scanner-{datetime.now().strftime('%Y-%m-%d')}.log"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # nigdy nie blokuj skanowania przez problem z logiem


# ──────────────────────────────────────────────
# MAIN SCAN
# ──────────────────────────────────────────────
def scan_once(test_symbol: str | None = None) -> None:
    ex = get_exchange()
    regime = btc_regime(ex)
    if regime.get("ok"):
        log(f"BTC regime: ${regime['close']:.0f} ({regime['change_24h']:+.2f}% 24h, {'RISK-OFF' if regime['risk_off'] else 'RISK-ON'})")
    else:
        log("BTC regime: UNKNOWN (fetch failed)")

    cooldowns = load_cooldown()
    signals_found = []
    errors = 0

    watchlist = (
        {test_symbol: config.WATCHLIST.get(test_symbol, {"tier": 1, "setups": ["A", "B", "C", "D"]})}
        if test_symbol
        else config.WATCHLIST
    )

    for symbol, meta in watchlist.items():
        tier = meta["tier"]
        setups_to_run = meta["setups"]

        # BTC regime filter — memy tylko gdy risk-on
        if tier == 4 and regime.get("risk_off"):
            continue

        df = fetch_ohlcv(ex, symbol, config.PRIMARY_TF, config.CANDLES_LIMIT)
        if df.empty or len(df) < 200:
            errors += 1
            continue

        atr_val = atr(df, 14)

        for setup_code in setups_to_run:
            fn = SETUP_FUNCTIONS[setup_code]
            min_conf = config.MIN_CONFLUENCES[setup_code]
            try:
                signal = fn(df, min_confluences=min_conf)
            except Exception as e:
                log(f"  ERROR {symbol} {setup_code}: {e}")
                continue

            if signal is None:
                continue

            # Cooldown check (jedno alert per aktywum-setup-direction per 4h)
            cd_key = f"{symbol}:{setup_code}:{signal['direction']}"
            if in_cooldown(cd_key, cooldowns):
                continue

            # Wzbogacenie sygnału
            signal["ticker"] = symbol.replace("/USDT:USDT", "USDT.P").replace("/", "")
            signal["exchange"] = "GATEIO"
            signal["timeframe"] = config.PRIMARY_TF
            signal["time"] = df["ts"].iloc[-1].isoformat()
            signal["atr"] = atr_val

            # Position sizing
            sizing = risk_summary(config.CAPITAL_GATE, signal, risk_pct=config.RISK_PER_TRADE_PCT, atr_value=atr_val)

            # Net R/R filter — tylko dla algo setups (E = trader-driven, exit manual)
            if setup_code in getattr(config, "RR_FILTER_SETUPS", ["A", "B", "C", "D"]):
                if sizing.get("rr_netto", 0) < config.MIN_RR_NETTO:
                    log(f"  SKIP {symbol} {setup_code} {signal['direction']} — R/R netto {sizing.get('rr_netto'):.2f} < {config.MIN_RR_NETTO}")
                    continue

            signals_found.append((signal, sizing))
            cooldowns[cd_key] = time.time()

            log(
                f"  SIGNAL {symbol} {setup_code} {signal['direction']} "
                f"@ {signal['entry']:.4f} | {signal['score']}/{signal['max_score']} konfl. | "
                f"R/R netto {sizing['rr_netto']:.2f}"
            )

            result = send_alert(signal, sizing)
            log(f"    -> notify: {result}")

    save_cooldown(cooldowns)
    log(f"Scan done. Signals: {len(signals_found)}, errors: {errors}, scanned: {len(watchlist)}")
    # Na Lambdzie chcemy strukturę (signals, errors) — bez breaking zmian dla CLI
    if getattr(config, "IS_LAMBDA", False):
        return {"signals": signals_found, "errors": errors, "scanned": len(watchlist)}
    return signals_found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Uruchom w pętli co 15 min")
    parser.add_argument("--test", type=str, default=None, help="Test pojedynczego aktywum (np. BTC)")
    parser.add_argument("--interval", type=int, default=900, help="Interwał loop w sekundach (default 900=15min)")
    parser.add_argument("--notify-start", action="store_true", help="Wyślij Telegram 'scanner started'")
    args = parser.parse_args()

    test_symbol = None
    if args.test:
        test_symbol = f"{args.test.upper()}/USDT:USDT"

    if args.notify_start:
        send_text(f"🤖 Scanner STARTED @ {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if args.loop:
        log(f"Scanner loop started, interval={args.interval}s")
        while True:
            try:
                scan_once(test_symbol)
            except KeyboardInterrupt:
                log("Interrupted")
                break
            except Exception as e:
                log(f"FATAL: {e}")
            log(f"Sleeping {args.interval}s...")
            time.sleep(args.interval)
    else:
        scan_once(test_symbol)


if __name__ == "__main__":
    main()
