import uuid
import httpx
from app import config
from app.models import PaymentRequest

def _get_token() -> str:
    r = httpx.post(f"{config.PAYPAL_BASE_URL}/v1/oauth2/token",
                   auth=(config.PAYPAL_CLIENT_ID, config.PAYPAL_CLIENT_SECRET),
                   data={"grant_type": "client_credentials"}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def send_payout(req: PaymentRequest) -> str:
    """Sends the money and returns PayPal's batch id."""
    r = httpx.post(f"{config.PAYPAL_BASE_URL}/v1/payments/payouts",
        headers={"Authorization": f"Bearer {_get_token()}"},
        json={"sender_batch_header": {"sender_batch_id": str(uuid.uuid4()),
                                      "email_subject": "Payment"},
              "items": [{"recipient_type": "EMAIL", "receiver": req.payee_email,
                         "amount": {"value": f"{req.amount:.2f}", "currency": req.currency}}]},
        timeout=15)
    r.raise_for_status()
    return r.json()["batch_header"]["payout_batch_id"]