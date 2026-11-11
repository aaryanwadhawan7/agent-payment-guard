import httpx
from app import config

def notify_pending(decision_id: int, req, reasons: list[str]) -> None:
    if not config.ZAPIER_WEBHOOK_URL:
        return
    try:
        httpx.post(config.ZAPIER_WEBHOOK_URL, timeout=5, json={
            "decision_id": decision_id, "vendor": req.vendor_name,
            "amount": str(req.amount), "currency": req.currency,
            "reasons": reasons, "dashboard": config.PUBLIC_URL})
    except httpx.HTTPError:
        pass   # an alert failure must never break the payment flow