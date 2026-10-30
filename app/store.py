from datetime import datetime, timezone
from itertools import count
from typing import Optional
from app.models import Decision, PaymentRequest

_log: list[dict] = []
_ids = count(1)

def add(req: PaymentRequest, decision: Decision, payout_batch_id: Optional[str] = None) -> dict:
    entry = {"id": next(_ids),
             "time": datetime.now(timezone.utc).isoformat(),
             "request": req.model_dump(mode="json"),
             "verdict": decision.verdict.value,
             "reasons": decision.reasons,
             "payout_batch_id": payout_batch_id}
    _log.append(entry)
    return entry

def list_entries() -> list[dict]:
    return list(reversed(_log))     # newest first