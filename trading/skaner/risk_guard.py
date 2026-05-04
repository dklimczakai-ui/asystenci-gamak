"""
Risk Guard — Circuit Breakers dla Daniel's trading system.

Chroni kapitał przed scenariuszami które zabiły autora "I Gave Claude Code $200k":
- SL streak 8 z rzędu → auto-pause 24h
- Daily loss >= 20% → STOP do końca dnia (Europe/Warsaw)
- Weekly loss >= 30% → STOP do niedzieli

Integracja ze scannerem: przed wysłaniem alertu scanner woła should_allow_alert().
Integracja z webhookiem (manual w MVP): Daniel wpisuje outcome przez CLI po zamknięciu tradu.

State trzymany w reports/risk_guard_state.json (survive cold start Lambdy, bo
na Lambdzie zapiszemy do S3 w Fazie 5 lub używamy DynamoDB — TBD).

CLI:
    python risk_guard.py status
    python risk_guard.py record --symbol BTC --outcome SL --r -1.0
    python risk_guard.py record --symbol BTC --outcome WIN --r 2.5
    python risk_guard.py reset-streak
    python risk_guard.py reset-daily
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

# Windows cp1250 nie obsługuje emoji — wymuś UTF-8 na stdout
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import config

# ───────── STORAGE BACKEND ─────────
# Lokalny plik jest default. Dla Lambdy (ephemeral /tmp) ustaw env vars:
#   RISK_GUARD_S3_BUCKET — nazwa bucketa
#   RISK_GUARD_S3_KEY    — klucz obiektu (domyślnie "risk_guard/state.json")
# IAM role Lambdy musi mieć: s3:GetObject, s3:PutObject scoped do tego ARN.
S3_BUCKET = os.getenv("RISK_GUARD_S3_BUCKET", "").strip()
S3_KEY = os.getenv("RISK_GUARD_S3_KEY", "risk_guard/state.json").strip()
USE_S3 = bool(S3_BUCKET)

WARSAW_TZ = ZoneInfo("Europe/Warsaw")

STATE_FILE = config.REPORTS_DIR / "risk_guard_state.json"

# Progi — nadpisywalne przez config.py jeśli Daniel chce je tam mieć centralnie
SL_STREAK_LIMIT = 8                 # 8 SL z rzędu → pauza
SL_STREAK_PAUSE_HOURS = 24          # ile godzin pauzy po przekroczeniu
DAILY_LOSS_PCT_LIMIT = getattr(config, "MAX_DAILY_LOSS_PCT", 20.0)
WEEKLY_LOSS_PCT_LIMIT = 30.0
MONTHLY_LOSS_PCT_LIMIT = 50.0

VALID_OUTCOMES = ("WIN", "SL", "TP1", "TP2", "BE", "PARTIAL")


@dataclass
class TradeRecord:
    ts: str          # ISO Europe/Warsaw
    symbol: str
    outcome: str     # jeden z VALID_OUTCOMES
    r_multiple: float
    notes: str = ""


@dataclass
class GuardState:
    trades: list[TradeRecord] = field(default_factory=list)
    sl_streak: int = 0
    pause_until_iso: Optional[str] = None  # ISO UTC; None = brak pauzy
    manual_stop: bool = False               # Daniel może ręcznie STOP
    manual_stop_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "trades": [asdict(t) for t in self.trades],
            "sl_streak": self.sl_streak,
            "pause_until_iso": self.pause_until_iso,
            "manual_stop": self.manual_stop,
            "manual_stop_reason": self.manual_stop_reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GuardState":
        return cls(
            trades=[TradeRecord(**t) for t in d.get("trades", [])],
            sl_streak=d.get("sl_streak", 0),
            pause_until_iso=d.get("pause_until_iso"),
            manual_stop=d.get("manual_stop", False),
            manual_stop_reason=d.get("manual_stop_reason", ""),
        )


def _load_from_s3() -> Optional[dict]:
    try:
        import boto3
        s3 = boto3.client("s3")
        resp = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
        return json.loads(resp["Body"].read().decode("utf-8"))
    except Exception as e:
        # 404 NoSuchKey = pierwszy run, zwracamy None → empty state
        if "NoSuchKey" in str(e) or "NotFound" in str(e):
            return None
        # Każdy inny błąd = bardzo ważna informacja, ale nie crashujemy scannera
        print(f"[risk_guard] S3 load error: {e}", file=sys.stderr)
        return None


def _save_to_s3(data: dict) -> None:
    try:
        import boto3
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=S3_KEY,
            Body=json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
    except Exception as e:
        print(f"[risk_guard] S3 save error: {e}", file=sys.stderr)


def load_state() -> GuardState:
    if USE_S3:
        data = _load_from_s3()
        return GuardState.from_dict(data) if data else GuardState()

    if not STATE_FILE.exists():
        return GuardState()
    try:
        return GuardState.from_dict(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except Exception:
        return GuardState()


def save_state(state: GuardState) -> None:
    if USE_S3:
        _save_to_s3(state.to_dict())
        return

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


# ───────── HELPERY CZASOWE ─────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_warsaw() -> datetime:
    return datetime.now(WARSAW_TZ)


def _parse_ts(iso: str) -> datetime:
    """Bezpieczny parser ISO z fallback."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return _now_utc() - timedelta(days=365)  # sentinel: stary


def _is_same_day_warsaw(ts_iso: str, ref: Optional[datetime] = None) -> bool:
    ref = ref or _now_warsaw()
    ts = _parse_ts(ts_iso).astimezone(WARSAW_TZ)
    return ts.date() == ref.date()


def _is_same_week_warsaw(ts_iso: str, ref: Optional[datetime] = None) -> bool:
    ref = ref or _now_warsaw()
    ts = _parse_ts(ts_iso).astimezone(WARSAW_TZ)
    # ISO week (poniedziałek–niedziela)
    return ts.isocalendar()[:2] == ref.isocalendar()[:2]


# ───────── GUARDS ─────────

def check_sl_streak(state: GuardState) -> tuple[bool, str]:
    """True = OK, False = blokuj."""
    if state.sl_streak < SL_STREAK_LIMIT:
        return True, f"SL streak: {state.sl_streak}/{SL_STREAK_LIMIT}"
    return False, (
        f"SL streak {state.sl_streak} ≥ limit {SL_STREAK_LIMIT}. "
        f"System pauzuje na {SL_STREAK_PAUSE_HOURS}h. "
        f"Reset: python risk_guard.py reset-streak (po review)."
    )


def check_pause(state: GuardState) -> tuple[bool, str]:
    if not state.pause_until_iso:
        return True, "Brak pauzy"
    pause_until = _parse_ts(state.pause_until_iso)
    now = _now_utc()
    if now >= pause_until:
        # Pauza wygasła — wyczyść
        state.pause_until_iso = None
        save_state(state)
        return True, "Pauza wygasła (auto-clear)"
    remaining = pause_until - now
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    return False, f"PAUZA {hours}h{minutes}m do {pause_until.astimezone(WARSAW_TZ).strftime('%Y-%m-%d %H:%M')}"


def check_daily_loss(state: GuardState) -> tuple[bool, str, float]:
    """Zsumuj R-multiples z dzisiejszych tradów. Jeśli loss > DAILY_LOSS_PCT_LIMIT% kapitału → STOP."""
    today_r = sum(
        t.r_multiple for t in state.trades if _is_same_day_warsaw(t.ts)
    )
    # Risk per trade = 10% (z config), więc 1R = 10% kapitału
    # Daily loss % = today_r × RISK_PER_TRADE_PCT (jeśli today_r < 0)
    risk_pct = getattr(config, "RISK_PER_TRADE_PCT", 10.0)
    daily_loss_pct = -today_r * risk_pct if today_r < 0 else 0.0
    if daily_loss_pct >= DAILY_LOSS_PCT_LIMIT:
        return False, (
            f"DAILY LOSS {daily_loss_pct:.1f}% ≥ limit {DAILY_LOSS_PCT_LIMIT}%. "
            f"STOP do końca dnia (reset automatyczny o północy Europe/Warsaw)."
        ), daily_loss_pct
    return True, f"Daily loss: {daily_loss_pct:.1f}% / {DAILY_LOSS_PCT_LIMIT}%", daily_loss_pct


def check_weekly_loss(state: GuardState) -> tuple[bool, str, float]:
    week_r = sum(
        t.r_multiple for t in state.trades if _is_same_week_warsaw(t.ts)
    )
    risk_pct = getattr(config, "RISK_PER_TRADE_PCT", 10.0)
    weekly_loss_pct = -week_r * risk_pct if week_r < 0 else 0.0
    if weekly_loss_pct >= WEEKLY_LOSS_PCT_LIMIT:
        return False, (
            f"WEEKLY LOSS {weekly_loss_pct:.1f}% ≥ limit {WEEKLY_LOSS_PCT_LIMIT}%. "
            f"STOP do niedzieli. Review strategii w weekend."
        ), weekly_loss_pct
    return True, f"Weekly loss: {weekly_loss_pct:.1f}% / {WEEKLY_LOSS_PCT_LIMIT}%", weekly_loss_pct


def check_manual_stop(state: GuardState) -> tuple[bool, str]:
    if state.manual_stop:
        return False, f"MANUAL STOP: {state.manual_stop_reason or 'bez powodu'}"
    return True, "Brak manual stop"


def should_allow_alert(symbol: str = "") -> tuple[bool, str]:
    """
    Główna funkcja integracyjna dla scanner_mtf.py.

    Returns: (allowed, reason)
    """
    state = load_state()

    # Kolejność: manual stop → pauza → SL streak → daily → weekly
    # Pierwszy fail = blokada.
    checks = [
        check_manual_stop(state),
        check_pause(state),
        check_sl_streak(state),
    ]
    daily_ok, daily_msg, _ = check_daily_loss(state)
    weekly_ok, weekly_msg, _ = check_weekly_loss(state)
    checks.append((daily_ok, daily_msg))
    checks.append((weekly_ok, weekly_msg))

    for allowed, msg in checks:
        if not allowed:
            return False, f"[risk_guard] {msg}"

    return True, "[risk_guard] OK"


# ───────── RECORD OUTCOMES ─────────

def record_outcome(symbol: str, outcome: str, r_multiple: float, notes: str = "") -> GuardState:
    """
    Zapisz wynik tradu. Aktualizuje SL streak.

    outcome: WIN | SL | TP1 | TP2 | BE | PARTIAL
    r_multiple: realny R (np. -1.0 dla SL, +2.3 dla TP2 częściowy)
    """
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"Invalid outcome '{outcome}'. Valid: {VALID_OUTCOMES}")

    state = load_state()

    # SL streak logika:
    # SL z r_multiple <= 0 → increment streak
    # WIN / TP / BE / PARTIAL z r_multiple > 0 → reset streak
    if outcome == "SL" or r_multiple <= 0:
        state.sl_streak += 1
    else:
        state.sl_streak = 0

    trade = TradeRecord(
        ts=_now_warsaw().isoformat(timespec="seconds"),
        symbol=symbol,
        outcome=outcome,
        r_multiple=r_multiple,
        notes=notes,
    )
    state.trades.append(trade)

    # Trim — trzymamy ostatnie 500 tradów
    if len(state.trades) > 500:
        state.trades = state.trades[-500:]

    # Auto-pauza po 8 SL z rzędu
    if state.sl_streak >= SL_STREAK_LIMIT:
        pause_until = _now_utc() + timedelta(hours=SL_STREAK_PAUSE_HOURS)
        state.pause_until_iso = pause_until.isoformat()

    save_state(state)
    return state


def reset_sl_streak(note: str = "manual reset") -> GuardState:
    state = load_state()
    state.sl_streak = 0
    state.pause_until_iso = None
    save_state(state)
    return state


def reset_daily(note: str = "manual reset") -> GuardState:
    """Usuwa trady z dzisiaj (po review / błąd wpisu)."""
    state = load_state()
    state.trades = [t for t in state.trades if not _is_same_day_warsaw(t.ts)]
    save_state(state)
    return state


def set_manual_stop(reason: str) -> GuardState:
    state = load_state()
    state.manual_stop = True
    state.manual_stop_reason = reason
    save_state(state)
    return state


def clear_manual_stop() -> GuardState:
    state = load_state()
    state.manual_stop = False
    state.manual_stop_reason = ""
    save_state(state)
    return state


# ───────── STATUS ─────────

def status_report() -> str:
    state = load_state()

    allowed, reason = should_allow_alert()
    sl_ok, sl_msg = check_sl_streak(state)
    pause_ok, pause_msg = check_pause(state)
    daily_ok, daily_msg, daily_pct = check_daily_loss(state)
    weekly_ok, weekly_msg, weekly_pct = check_weekly_loss(state)
    manual_ok, manual_msg = check_manual_stop(state)

    today_trades = [t for t in state.trades if _is_same_day_warsaw(t.ts)]
    week_trades = [t for t in state.trades if _is_same_week_warsaw(t.ts)]
    today_r = sum(t.r_multiple for t in today_trades)
    week_r = sum(t.r_multiple for t in week_trades)

    status = "🟢 OK — alerty przechodzą" if allowed else f"🔴 ZABLOKOWANE — {reason}"

    lines = [
        "━━━━━ RISK GUARD STATUS ━━━━━",
        f"Status: {status}",
        "",
        "GUARDS:",
        f"  SL streak: {sl_msg}",
        f"  Pauza:     {pause_msg}",
        f"  Daily:     {daily_msg}",
        f"  Weekly:    {weekly_msg}",
        f"  Manual:    {manual_msg}",
        "",
        "DZISIAJ (Europe/Warsaw):",
        f"  Trady: {len(today_trades)}",
        f"  Suma R: {today_r:+.2f}",
        f"  Loss %: {daily_pct:.1f}%",
        "",
        "TEN TYDZIEŃ:",
        f"  Trady: {len(week_trades)}",
        f"  Suma R: {week_r:+.2f}",
        f"  Loss %: {weekly_pct:.1f}%",
        "",
        f"OSTATNIE 10 TRADÓW:",
    ]
    for t in state.trades[-10:]:
        lines.append(f"  [{t.ts[:16]}] {t.symbol:20} {t.outcome:8} {t.r_multiple:+.2f}R  {t.notes}")
    if not state.trades:
        lines.append("  (brak)")

    return "\n".join(lines)


# ───────── CLI ─────────

def main():
    parser = argparse.ArgumentParser(description="Risk Guard CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Pokaż stan systemu")

    p_rec = sub.add_parser("record", help="Zapisz wynik tradu")
    p_rec.add_argument("--symbol", required=True)
    p_rec.add_argument("--outcome", required=True, choices=list(VALID_OUTCOMES))
    p_rec.add_argument("--r", dest="r_multiple", type=float, required=True,
                       help="R multiple (np. -1.0 dla SL, +2.3 dla TP2)")
    p_rec.add_argument("--notes", default="")

    sub.add_parser("reset-streak", help="Ręcznie wyzeruj SL streak (po review)")
    sub.add_parser("reset-daily", help="Usuń trady z dzisiaj (korekta wpisów)")

    p_stop = sub.add_parser("manual-stop", help="Zatrzymaj system manualnie")
    p_stop.add_argument("--reason", default="Daniel decision")

    sub.add_parser("clear-stop", help="Wyczyść manual stop")

    p_test = sub.add_parser("test", help="Symuluj 8 SL z rzędu (sanity check)")
    p_test.add_argument("--real", action="store_true", help="Zapisz naprawdę (bez = dry)")

    args = parser.parse_args()

    if args.cmd == "status":
        print(status_report())
        return

    if args.cmd == "record":
        state = record_outcome(args.symbol, args.outcome, args.r_multiple, args.notes)
        print(f"✅ Zapisano. SL streak: {state.sl_streak}/{SL_STREAK_LIMIT}")
        if state.pause_until_iso:
            print(f"⚠️  Pauza włączona do {state.pause_until_iso}")
        return

    if args.cmd == "reset-streak":
        state = reset_sl_streak()
        print(f"✅ SL streak zresetowany. Stan: {state.sl_streak}")
        return

    if args.cmd == "reset-daily":
        state = reset_daily()
        print(f"✅ Dzienne trady usunięte. Total w bazie: {len(state.trades)}")
        return

    if args.cmd == "manual-stop":
        state = set_manual_stop(args.reason)
        print(f"🔴 Manual stop włączony: {state.manual_stop_reason}")
        return

    if args.cmd == "clear-stop":
        state = clear_manual_stop()
        print("✅ Manual stop wyczyszczony")
        return

    if args.cmd == "test":
        if not args.real:
            print("[dry-run] Symuluję 8 SL z rzędu — użyj --real żeby zapisać")
            return
        for i in range(SL_STREAK_LIMIT):
            state = record_outcome("TEST/USDT", "SL", -1.0, f"sanity test #{i+1}")
        print("✅ Test done:")
        print(status_report())


if __name__ == "__main__":
    main()
