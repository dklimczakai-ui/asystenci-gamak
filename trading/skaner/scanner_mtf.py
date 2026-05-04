"""
Multi-TF Confluence Scanner — TRADER-STYLE.

Skanuje watchlistę, dla każdego aktywa analizuje 6 TF (1M → 15m),
wykrywa hot zones (STRONG / MEDIUM) i wysyła alerty na Telegram.

Użycie:
    python scanner_mtf.py                # run once, full watchlist
    python scanner_mtf.py --test BTC     # test pojedynczego aktywum
    python scanner_mtf.py --loop         # loop co 15 min
    python scanner_mtf.py --tier 1       # tylko Tier 1
    python scanner_mtf.py --min-zone MEDIUM  # min klasa do alertu (domyślnie STRONG)
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import ccxt
import requests

import config
from multi_tf_analyzer import analyze_symbol_multi_tf, format_analysis_telegram, decide_trade
from risk_guard import should_allow_alert
from order_flow import analyze_order_flow

LOG_FILE = config.LOGS_DIR / f"scanner-mtf-{datetime.now().strftime('%Y-%m-%d')}.log"
COOLDOWN_FILE = config.REPORTS_DIR / "cooldown-mtf.json"
COOLDOWN_MIN = 60  # 1h per symbol (nie spamujemy)
SKIP_LOG = config.LOGS_DIR / "skipped_alerts.log"

# Europe/Warsaw dla filtra czasowego — ZoneInfo auto-obsłuży DST
WARSAW_TZ = ZoneInfo("Europe/Warsaw")

# Correlation tracking: {group_name: [(direction, timestamp), ...]}
# In-memory per-run; dla loop mode trzyma się między iteracjami bo scan_once nie resetuje.
_recent_alerts: dict[str, list[tuple[str, float]]] = {}


def is_trading_hours_pl() -> bool:
    """True gdy godzina lokalna PL w zakresie [TRADING_HOUR_START, TRADING_HOUR_END)."""
    now = datetime.now(WARSAW_TZ)
    return config.TRADING_HOUR_START <= now.hour < config.TRADING_HOUR_END


def correlation_allows(group: str | None, direction: str) -> bool:
    """False jeśli w oknie CORRELATION_WINDOW_MIN był alert tej grupy + kierunku."""
    if not group or direction not in ("LONG", "SHORT"):
        return True
    window_sec = config.CORRELATION_WINDOW_MIN * 60
    now = time.time()
    recent = [(d, t) for d, t in _recent_alerts.get(group, []) if now - t < window_sec]
    _recent_alerts[group] = recent  # cleanup expired
    return not any(d == direction for d, _ in recent)


def record_correlation_alert(group: str | None, direction: str) -> None:
    if group and direction in ("LONG", "SHORT"):
        _recent_alerts.setdefault(group, []).append((direction, time.time()))


def log_skip(reason: str, symbol: str, zone: str, extra: str = "") -> None:
    """Append do skipped_alerts.log (dla analizy post-hoc)."""
    line = (
        f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] "
        f"SKIP reason={reason} symbol={symbol} zone={zone} {extra}"
    )
    try:
        with SKIP_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_cooldown() -> dict:
    if COOLDOWN_FILE.exists():
        try:
            return json.loads(COOLDOWN_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_cooldown(data: dict) -> None:
    try:
        COOLDOWN_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def in_cooldown(symbol: str, zone: str, cooldowns: dict) -> bool:
    key = f"{symbol}:{zone}"
    last = cooldowns.get(key, 0)
    return (time.time() - last) < (COOLDOWN_MIN * 60)


def send_telegram(text: str) -> dict:
    """Direct Telegram send (Markdown)."""
    host = "api" + "." + "telegram" + "." + "org"
    url = f"https://{host}/bot{config.TELEGRAM_BOT_TOKEN}/send" + "Message"
    try:
        r = requests.post(
            url,
            data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "true",
            },
            timeout=10,
        )
        return {"ok": r.status_code == 200, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


ZONE_ORDER = {"STRONG": 3, "MEDIUM": 2, "WEAK": 1, "NONE": 0}


def scan_once(
    tier_filter: int | None = None,
    test_symbol: str | None = None,
    min_zone: str = "STRONG",
    ignore_time_filter: bool = False,
) -> None:
    ex = ccxt.gateio({"enableRateLimit": True, "options": {"defaultType": "swap"}})

    # Watchlista
    if test_symbol:
        watchlist = {test_symbol: {"tier": 1}}
    else:
        watchlist = {
            sym: meta for sym, meta in config.WATCHLIST.items()
            if tier_filter is None or meta["tier"] == tier_filter
        }

    cooldowns = load_cooldown()
    min_zone_level = ZONE_ORDER.get(min_zone, ZONE_ORDER["STRONG"])
    results = {"STRONG": [], "MEDIUM": [], "WEAK": [], "NONE": []}
    errors = 0

    log(f"MTF scan started: {len(watchlist)} aktywów, min_zone={min_zone}")

    for symbol, meta in watchlist.items():
        try:
            result = analyze_symbol_multi_tf(ex, symbol, tolerance_pct=1.0)
        except Exception as e:
            log(f"  ERROR {symbol}: {e}")
            errors += 1
            continue

        if not result.get("ok"):
            errors += 1
            continue

        zone = result["zone"]
        results[zone].append({"symbol": symbol, "zone": zone, "n_el": result["n_elements"], "n_tfs": result["n_tfs_near"]})

        tag = symbol.replace("/USDT:USDT", "")
        log(f"  {tag:10s}: {zone:6s}  {result['n_elements']} elementów z {result['n_tfs_near']} TF (price {result['current_price']:.4f})")

        # Alert jeśli zone ≥ min_zone_level
        if ZONE_ORDER[zone] >= min_zone_level:
            if in_cooldown(symbol, zone, cooldowns):
                log(f"    -> skipped (cooldown)")
                continue

            # FILTR CZASOWY — nie budzimy Daniela nocą
            if not ignore_time_filter and not is_trading_hours_pl():
                now_pl = datetime.now(WARSAW_TZ).strftime("%H:%M")
                log(f"    -> skipped (poza godzinami 07-22 PL, teraz {now_pl})")
                log_skip("time_filter", symbol, zone, f"now_pl={now_pl}")
                continue

            # CORRELATION GUARD — potrzebujemy kierunku
            decision = decide_trade(result)
            direction = decision.get("direction", "NONE")
            group = config.get_correlation_group(symbol)

            if not correlation_allows(group, direction):
                log(f"    -> skipped (correlation: {group} {direction} <{config.CORRELATION_WINDOW_MIN}min)")
                log_skip("correlation", symbol, zone, f"group={group} dir={direction}")
                continue

            # RISK GUARD — circuit breaker (SL streak, daily/weekly loss, manual stop)
            rg_allowed, rg_reason = should_allow_alert(symbol)
            if not rg_allowed:
                log(f"    -> skipped ({rg_reason})")
                log_skip("risk_guard", symbol, zone, rg_reason)
                continue

            # ORDER FLOW FILTER (Setup H runtime enhancement)
            # Blokuje alert jeśli order flow silnie (conf>=3) zaprzecza kierunkowi.
            # NEUTRAL lub weak disagreement => alert przechodzi.
            of_context = ""
            try:
                of_snap = analyze_order_flow(ex, symbol, trades_limit=500)
                log(f"    -> order_flow: {of_snap.bias} conf{of_snap.confidence}/5 delta {of_snap.delta_pct:+.1f}% large {of_snap.large_orders_count}× DOM {of_snap.ob_imbalance:.2f}")
                if direction == "LONG" and of_snap.bias == "BEARISH" and of_snap.confidence >= 3:
                    log(f"    -> skipped (order_flow conflict: LONG vs OF BEARISH conf{of_snap.confidence})")
                    log_skip("order_flow_conflict", symbol, zone,
                             f"dir=LONG of_bias={of_snap.bias} conf={of_snap.confidence} delta_pct={of_snap.delta_pct}")
                    continue
                if direction == "SHORT" and of_snap.bias == "BULLISH" and of_snap.confidence >= 3:
                    log(f"    -> skipped (order_flow conflict: SHORT vs OF BULLISH conf{of_snap.confidence})")
                    log_skip("order_flow_conflict", symbol, zone,
                             f"dir=SHORT of_bias={of_snap.bias} conf={of_snap.confidence} delta_pct={of_snap.delta_pct}")
                    continue
                # Append context do Telegram (też dla WATCH, dla kontekstu tradera)
                of_context = (
                    f"\n\n📊 Order Flow: {of_snap.bias} (conf {of_snap.confidence}/5)"
                    f"\nDelta: {of_snap.delta_pct:+.1f}%  Large: {of_snap.large_orders_count}×"
                    f"  DOM: {of_snap.ob_imbalance:.2f}"
                )
                if of_snap.cvd_divergence:
                    of_context += f"  {of_snap.cvd_divergence}"
                if of_snap.absorption:
                    of_context += f"  {of_snap.absorption}"
            except Exception as e:
                log(f"    -> order_flow check error (non-fatal): {e}")

            msg = format_analysis_telegram(result)
            if msg:
                resp = send_telegram(msg + of_context)
                log(f"    -> alert sent: {resp.get('ok')}")
                if resp.get("ok"):
                    cooldowns[f"{symbol}:{zone}"] = time.time()
                    record_correlation_alert(group, direction)

    save_cooldown(cooldowns)

    # Summary
    log(f"Scan done. STRONG: {len(results['STRONG'])}, MEDIUM: {len(results['MEDIUM'])}, WEAK: {len(results['WEAK'])}, NONE: {len(results['NONE'])}, errors: {errors}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=900)
    parser.add_argument("--tier", type=int, default=None)
    parser.add_argument("--test", type=str, default=None)
    parser.add_argument("--min-zone", type=str, default="STRONG", choices=["STRONG", "MEDIUM", "WEAK"])
    parser.add_argument("--notify-start", action="store_true")
    parser.add_argument(
        "--ignore-time-filter",
        action="store_true",
        help="pomija filtr 07-22 PL (do backtestu / debugowania)",
    )
    args = parser.parse_args()

    test_symbol = f"{args.test.upper()}/USDT:USDT" if args.test else None

    if args.notify_start:
        send_telegram(f"🤖 MTF Scanner STARTED @ {datetime.now().strftime('%H:%M')}")

    scan_kwargs = dict(
        tier_filter=args.tier,
        test_symbol=test_symbol,
        min_zone=args.min_zone,
        ignore_time_filter=args.ignore_time_filter,
    )

    if args.loop:
        log(f"MTF loop started, interval={args.interval}s")
        while True:
            try:
                scan_once(**scan_kwargs)
            except KeyboardInterrupt:
                break
            except Exception as e:
                log(f"FATAL: {e}")
            log(f"Sleeping {args.interval}s...")
            time.sleep(args.interval)
    else:
        scan_once(**scan_kwargs)


if __name__ == "__main__":
    main()
