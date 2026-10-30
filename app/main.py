from fastapi import FastAPI, HTTPException
import httpx
from app import paypal_client, policy, store
from app.models import PayResponse, PaymentRequest, Verdict

app = FastAPI(title="Agent Payment Guard", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/pay", response_model=PayResponse)
def pay(req: PaymentRequest):
    decision = policy.evaluate(req)
    batch_id = None
    if decision.verdict == Verdict.ALLOW:       # only safe payments go to PayPal
        try:
            batch_id = paypal_client.send_payout(req)
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="PayPal request failed")
    entry = store.add(req, decision, batch_id)
    return PayResponse(decision_id=entry["id"], verdict=decision.verdict,
                       reasons=decision.reasons, payout_batch_id=batch_id)

@app.get("/decisions")
def decisions():
    return store.list_entries()