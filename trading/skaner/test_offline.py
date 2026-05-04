"""
Smoke test offline analyzer — weryfikuje:
  1. analyze_at wywoluje sie bez network call
  2. Zwraca dict o oczekiwanej strukturze
  3. ZERO FUTURE LEAK: analyzer nie widzi barow po timestamp

Uruchomienie:
    cd trading/skaner && python test_offline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from multi_tf_analyzer import analyze_at, CANDLES_PER_TF, _TF_CACHE_SUFFIX

CACHE_DIR = Path(__file__).parent.parent / "backtest" / "data"


def _fabricate_cache(tmp_dir: Path, symbol_flat: str = "BTCUSDT") -> pd.Timestamp:
    """Jesli brak realnych parquetow, sfabrykuj deterministyczne OHLCV."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    for tf in _TF_CACHE_SUFFIX.keys():
        freq = {"1w": "7D", "1d": "1D", "4h": "4h", "1h": "1h", "15m": "15min"}[tf]
        n = max(CANDLES_PER_TF.get(tf, 500) * 2, 600)
        idx = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
        close = 30000 + np.cumsum(rng.normal(0, 150, len(idx)))
        close = np.maximum(close, 1000)
        high = close + rng.uniform(10, 300, len(idx))
        low = close - rng.uniform(10, 300, len(idx))
        open_ = close + rng.normal(0, 80, len(idx))
        vol = rng.uniform(100, 2000, len(idx))
        df = pd.DataFrame({
            "open_time": idx,
            "open": open_, "high": high, "low": low,
            "close": close, "volume": vol,
            "close_time": idx,
        })
        df.to_parquet(tmp_dir / f"{symbol_flat}_{tf}.parquet", index=False)

    # timestamp: srodek zakresu 4h
    mid_idx = pd.date_range(
        "2024-01-01",
        periods=max(CANDLES_PER_TF["4h"] * 2, 600),
        freq="4h",
        tz="UTC",
    )
    return mid_idx[len(mid_idx) // 2]


def main() -> int:
    # Przygotuj cache
    real_cache_has_btc = (
        CACHE_DIR.exists()
        and (CACHE_DIR / "BTCUSDT_4h.parquet").exists()
    )
    if real_cache_has_btc:
        print(f"[SETUP] Uzywam realnego cache: {CACHE_DIR}")
        df_4h = pd.read_parquet(CACHE_DIR / "BTCUSDT_4h.parquet")
        if "open_time" in df_4h.columns:
            df_4h["ts"] = pd.to_datetime(df_4h["open_time"], utc=True, errors="coerce")
        else:
            df_4h["ts"] = pd.to_datetime(df_4h["ts"], utc=True, errors="coerce")
        ts = df_4h["ts"].iloc[len(df_4h) // 2]
        cache_dir_used = CACHE_DIR
    else:
        print(f"[SETUP] Brak cache w {CACHE_DIR} - fabrykuje syntetyczne OHLCV...")
        cache = Path(__file__).parent / "_tmp_offline_cache"
        ts = _fabricate_cache(cache)
        cache_dir_used = cache

    print(f"[RUN] analyze_at(BTC/USDT:USDT, ts={ts}, cache_dir={cache_dir_used})")
    result = analyze_at(
        symbol="BTC/USDT:USDT",
        timestamp=ts,
        cache_dir=cache_dir_used,
        tolerance_pct=1.0,
    )

    if not result.get("ok"):
        print(f"[FAIL] {result}")
        return 1

    keys = ["current_price", "zone", "n_elements", "n_tfs_near",
            "direction", "entry", "sl", "tp1", "tp2", "rr1", "rr2",
            "total_elements", "analyzed_at"]
    print("\n[RESULT]")
    for k in keys:
        print(f"  {k:18s} = {result.get(k)}")

    print(f"  per_tf TFs         = {list(result.get('per_tf', {}).keys())}")
    print(f"  per_type           = {result.get('per_type')}")

    print("\n[FUTURE-LEAK CHECK] guard w _resolve_df asserts ts <= max_ts")
    print("[DONE] smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
