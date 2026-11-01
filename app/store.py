import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional
from app import config
from app.models import Decision, PaymentRequest

@contextmanager
def _db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db() -> None:
    with _db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            payee_email TEXT NOT NULL,
            amount TEXT NOT NULL,
            currency TEXT NOT NULL,
            note TEXT,
            verdict TEXT NOT NULL,
            reasons TEXT NOT NULL,
            status TEXT NOT NULL,
            payout_batch_id TEXT)""")

def _to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["reasons"] = json.loads(d["reasons"])
    return d

def add(req: PaymentRequest, decision: Decision, status: str,
        batch_id: Optional[str] = None) -> int:
    with _db() as c:
        cur = c.execute(
            """INSERT INTO decisions (time, vendor_name, payee_email, amount, currency,
               note, verdict, reasons, status, payout_batch_id)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (datetime.now(timezone.utc).isoformat(), req.vendor_name, req.payee_email,
             str(req.amount), req.currency, req.note, decision.verdict.value,
             json.dumps(decision.reasons), status, batch_id))
        return cur.lastrowid

def get(decision_id: int) -> Optional[dict]:
    with _db() as c:
        row = c.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
    return _to_dict(row) if row else None

def list_entries() -> list[dict]:
    with _db() as c:
        rows = c.execute("SELECT * FROM decisions ORDER BY id DESC").fetchall()
    return [_to_dict(r) for r in rows]

def claim_pending(decision_id: int) -> bool:
    """Atomically move pending -> processing. Only one caller can win."""
    with _db() as c:
        cur = c.execute("UPDATE decisions SET status='processing' "
                        "WHERE id=? AND status='pending'", (decision_id,))
        return cur.rowcount == 1

def reject_pending(decision_id: int) -> bool:
    with _db() as c:
        cur = c.execute("UPDATE decisions SET status='rejected' "
                        "WHERE id=? AND status='pending'", (decision_id,))
        return cur.rowcount == 1

def set_status(decision_id: int, status: str, batch_id: Optional[str] = None) -> None:
    with _db() as c:
        c.execute("UPDATE decisions SET status=?, payout_batch_id=? WHERE id=?",
                  (status, batch_id, decision_id))