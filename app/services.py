import httpx
from fastapi import HTTPException

from app import injection, notify, paypal_client, policy, store
from app.models import PayResponse, PaymentRequest, Verdict

def process_payment(req: PaymentRequest) -> PayResponse:
    vendor = store.get_vendor(req.vendor_name)
    decision = policy.evaluate(req, vendor, extra=[injection.check_source(req)])
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
    if status == "pending":
        notify.notify_pending(decision_id, req, decision.reasons)
    return PayResponse(decision_id=decision_id, verdict=decision.verdict, status=status,
                       reasons=decision.reasons, payout_batch_id=batch_id)