"""
Diagnostyka — pokaż aktualny stan konfluencji bez progu.
Używaj do kalibracji filtra.
"""
import argparse

import ccxt
import pandas as pd

import config
from indicators import sma, anchored_vwap, stoch_rsi, squeeze_momentum, last_impulse_fib, pa_signals, atr
from setups import SETUP_FUNCTIONS


def diagnose(symbol: str, tf: str = "4h"):
    ex = getattr(ccxt, config.EXCHANGE_ID)({"enableRateLimit": True, "options": {"defaultType": "swap"}})
    print(f"\n=== DIAGNOZA {symbol} @ {tf} ===\n")

    data = ex.fetch_ohlcv(symbol, tf, limit=300)
    df = pd.DataFrame(data, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)

    close = df["close"].iloc[-1]
    print(f"Close: ${close:.4f} @ {df['ts'].iloc[-1]}")

    # MA
    ma50 = sma(df["close"], 50).iloc[-1]
    ma100 = sma(df["close"], 100).iloc[-1]
    ma200 = sma(df["close"], 200).iloc[-1]
    ma_state = "BULL" if ma50 > ma100 > ma200 else "BEAR" if ma50 < ma100 < ma200 else "MIXED"
    print(f"MA: 50=${ma50:.2f} 100=${ma100:.2f} 200=${ma200:.2f} => {ma_state}")

    # VWAP
    vwap = anchored_vwap(df, 96)
    print(f"VWAP (96 bar anchor): ${vwap:.2f} => close {'ABOVE' if close > vwap else 'BELOW'}")

    # Fib
    fib = last_impulse_fib(df)
    if fib:
        print(f"Fib (impulse {fib['direction']} {fib['move_pct']:.2f}%):")
        print(f"  swing_low=${fib['swing_low']:.2f}, swing_high=${fib['swing_high']:.2f}")
        print(f"  0.618=${fib['fib_618']:.2f}, 0.66=${fib['fib_66']:.2f}, 0.786=${fib['fib_786']:.2f}")
    else:
        print("Fib: brak wykrytego impulse leg >= 3%")

    # Stoch RSI
    k, d = stoch_rsi(df["close"])
    print(f"Stoch RSI: K={k.iloc[-1]:.1f} D={d.iloc[-1]:.1f}")

    # Squeeze
    sqz_on, sqz_release, mom = squeeze_momentum(df)
    print(f"Squeeze: on={sqz_on}, release={sqz_release}, momentum={mom:+.4f}")

    # PA
    pa = pa_signals(df)
    print(f"PA: bullish={pa['pa_bullish']}, bearish={pa['pa_bearish']}")

    # ATR
    atr_val = atr(df, 14)
    print(f"ATR(14): ${atr_val:.4f} ({atr_val/close*100:.2f}%)")

    # Setup ocena
    print(f"\n--- SETUPY (scoring bez progu) ---")
    for code, fn in SETUP_FUNCTIONS.items():
        res = fn(df, min_confluences=0)  # no threshold
        if res:
            print(f"  {code}: {res['direction']} {res['score']}/{res['max_score']} konfl.")
            print(f"     details: {res['details']}")
            print(f"     entry={res['entry']:.4f} sl={res['sl']:.4f} tp={res['tp']:.4f} rr={res['rr']}")
        else:
            print(f"  {code}: brak sygnału (< min confluences nawet przy progu 0)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", nargs="?", default="BTC")
    parser.add_argument("--tf", default="4h")
    args = parser.parse_args()
    sym = f"{args.symbol.upper()}/USDT:USDT"
    diagnose(sym, args.tf)
