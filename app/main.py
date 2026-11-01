import secrets
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse

from app import config, paypal_client, policy, store
from app.models import PayResponse, PaymentRequest, Verdict

STATIC = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()          # create the table on startup
    yield

app = FastAPI(title="Agent Payment Guard", version="0.2.0", lifespan=lifespan)

def require_admin(x_admin_token: str = Header(default="")):
    ok = secrets.compare_digest(x_admin_token.encode(), config.ADMIN_TOKEN.encode())
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid admin token")

@app.get("/")
def dashboard():
    return FileResponse(STATIC / "index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/pay", response_model=PayResponse)
def pay(req: PaymentRequest):
    decision = policy.evaluate(req)
    batch_id = None
    if decision.verdict == Verdict.ALLOW:
        try:
            batch_id = paypal_client.send_payout(req)
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="PayPal request failed")
        status = "paid"
    elif decision.verdict == Verdict.NEEDS_APPROVAL:
        status = "pending"
    else:
        status = "blocked"
    decision_id = store.add(req, decision, status, batch_id)
    return PayResponse(decision_id=decision_id, verdict=decision.verdict, status=status,
                       reasons=decision.reasons, payout_batch_id=batch_id)

@app.get("/decisions")
def decisions():
    return store.list_entries()

@app.post("/decisions/{decision_id}/approve", dependencies=[Depends(require_admin)])
def approve(decision_id: int):
    row = store.get(decision_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    if not store.claim_pending(decision_id):
        raise HTTPException(status_code=409, detail=f"Cannot approve: status is '{row['status']}'")
    req = PaymentRequest(vendor_name=row["vendor_name"], payee_email=row["payee_email"],
                         amount=Decimal(row["amount"]), currency=row["currency"],
                         note=row["note"])
    try:
        batch_id = paypal_client.send_payout(req)
    except httpx.HTTPError:
        store.set_status(decision_id, "pending")      # put it back so it can be retried
        raise HTTPException(status_code=502, detail="PayPal request failed")
    store.set_status(decision_id, "paid", batch_id)
    return {"decision_id": decision_id, "status": "paid", "payout_batch_id": batch_id}

@app.post("/decisions/{decision_id}/reject", dependencies=[Depends(require_admin)])
def reject(decision_id: int):
    if not store.reject_pending(decision_id):
        raise HTTPException(status_code=409, detail="Only pending decisions can be rejected")
    return {"decision_id": decision_id, "status": "rejected"}