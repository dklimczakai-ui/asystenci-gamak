"""
Download 2-year OHLCV history from Binance USD-M Futures.

Cache: trading/backtest/data/{SYMBOL}_{TF}.parquet
Okres: 2024-04-17 -> 2026-04-17 (2 lata)
TF: 1w, 1d, 4h, 1h, 15m (pomijamy 1M - za malo barow dla 2 lat)

Public endpoint - bez klucza, bez konta, anonimowy HTTP GET.
"""
from __future__ import annotations

import io
import json
import sys
import time

# Force UTF-8 stdout on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

BASE_URL = "https://fapi.binance.com/fapi/v1/klines"
EXCHANGE_INFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"
OUT_DIR = Path(__file__).parent / "data"
START_DATE = datetime(2024, 4, 17, tzinfo=timezone.utc)
END_DATE = datetime(2026, 4, 17, tzinfo=timezone.utc)

SYMBOLS = [
    # Tier 1
    "BTCUSDT", "SOLUSDT", "SUIUSDT", "TONUSDT", "AVAXUSDT",
    # Tier 2
    "HYPEUSDT", "PENDLEUSDT", "ONDOUSDT", "CRVUSDT", "RAYUSDT", "JUPUSDT",
    # Tier 3
    "TAOUSDT", "RENDERUSDT", "VIRTUALUSDT", "IMXUSDT", "SUPERUSDT",
    # Tier 4 (memy)
    "BONKUSDT", "BRETTUSDT", "FLOKIUSDT", "PENGUUSDT",
    "FARTCOINUSDT", "PUMPUSDT", "SPXUSDT",
    # Tier 5
    "KASUSDT", "SUSDT",
]

TIMEFRAMES = ["1w", "1d", "4h", "1h", "15m"]


def get_listed_symbols() -> set[str]:
    """Pre-filter: sprawdź które symbole w ogóle istnieją na Binance futures."""
    try:
        r = requests.get(EXCHANGE_INFO, timeout=15)
        data = r.json()
        return {s["symbol"] for s in data.get("symbols", [])
                if s.get("status") == "TRADING" and s.get("contractType") == "PERPETUAL"}
    except Exception as e:
        print(f"[WARN] exchangeInfo failed: {e} — skipping pre-filter")
        return set()


def fetch_klines(symbol: str, interval: str, start_ms: int, end_ms: int,
                 limit: int = 1000) -> Optional[list]:
    """Single request with retry + exponential backoff."""
    for attempt in range(3):
        try:
            r = requests.get(BASE_URL, params={
                "symbol": symbol,
                "interval": interval,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": limit,
            }, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 418):  # rate limited / IP banned temp
                sleep_s = 2 ** attempt * 5
                print(f"  [429] waiting {sleep_s}s...")
                time.sleep(sleep_s)
                continue
            if r.status_code == 400:
                # invalid symbol - treat as missing
                return None
            print(f"  [HTTP {r.status_code}] retry...")
            time.sleep(2 ** attempt)
        except requests.RequestException as e:
            print(f"  [NET ERR] {e} retry...")
            time.sleep(2 ** attempt)
    return None


def download_symbol_tf(symbol: str, tf: str) -> Optional[list]:
    """Paginated download full range. Returns None if symbol missing."""
    start_ms = int(START_DATE.timestamp() * 1000)
    end_ms = int(END_DATE.timestamp() * 1000)
    all_bars: list = []
    cur = start_ms
    while cur < end_ms:
        bars = fetch_klines(symbol, tf, cur, end_ms, 1000)
        if bars is None:
            return None  # symbol not on exchange
        if not bars:
            break
        all_bars.extend(bars)
        last_open = bars[-1][0]
        if last_open <= cur:
            break
        cur = last_open + 1
        time.sleep(0.1)  # be nice to API
    return all_bars


def bars_to_df(bars: list) -> pd.DataFrame:
    df = pd.DataFrame(bars, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_base", "taker_quote", "ignore"
    ])
    df = df[["open_time", "open", "high", "low", "close", "volume", "close_time"]].copy()
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    df = df.drop_duplicates(subset=["open_time"]).sort_values("open_time").reset_index(drop=True)
    return df


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Output dir: {OUT_DIR}")
    print(f"[INFO] Range: {START_DATE.date()} -> {END_DATE.date()}")
    print(f"[INFO] Assets: {len(SYMBOLS)} × TFs: {len(TIMEFRAMES)} = {len(SYMBOLS) * len(TIMEFRAMES)} files\n")

    listed = get_listed_symbols()
    missing: list[str] = []
    summary: list[dict] = []

    for i, sym in enumerate(SYMBOLS, 1):
        if listed and sym not in listed:
            print(f"[{i:2d}/{len(SYMBOLS)}] {sym}: NOT on Binance futures (all TFs)")
            for tf in TIMEFRAMES:
                missing.append(f"{sym} ({tf}): not listed on exchange")
            continue

        for tf in TIMEFRAMES:
            print(f"[{i:2d}/{len(SYMBOLS)}] {sym:14s} {tf:3s} ... ", end="", flush=True)
            bars = download_symbol_tf(sym, tf)
            if bars is None:
                print("MISSING (HTTP 400)")
                missing.append(f"{sym} ({tf}): HTTP 400")
                continue
            if not bars:
                print("NO DATA")
                missing.append(f"{sym} ({tf}): empty response")
                continue
            df = bars_to_df(bars)
            out = OUT_DIR / f"{sym}_{tf}.parquet"
            df.to_parquet(out, index=False)
            first = df["open_time"].iloc[0].date()
            last = df["open_time"].iloc[-1].date()
            days = (df["open_time"].iloc[-1] - df["open_time"].iloc[0]).days
            marker = "OK" if days >= 700 else "PARTIAL"
            print(f"{len(df):6d} bars ({first} -> {last}, {days}d) {marker}")
            summary.append({
                "symbol": sym, "tf": tf, "bars": len(df),
                "first": str(first), "last": str(last), "days": days,
            })

    # Write MISSING.md
    if missing:
        (OUT_DIR / "MISSING.md").write_text(
            "# Missing / partial data\n\n" + "\n".join(f"- {m}" for m in missing),
            encoding="utf-8",
        )

    # Write summary
    (OUT_DIR / "_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    # Final verification
    total_mb = sum(p.stat().st_size for p in OUT_DIR.glob("*.parquet")) / 1024 / 1024
    print(f"\n[DONE] {len(summary)} parquet files, {total_mb:.1f} MB total")
    print(f"[DONE] {len(missing)} missing entries — see MISSING.md")


if __name__ == "__main__":
    main()
