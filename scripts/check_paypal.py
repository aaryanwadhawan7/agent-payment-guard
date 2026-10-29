import os, uuid, httpx
from dotenv import load_dotenv

load_dotenv()                       # reads your secrets from .env
BASE = "https://api-m.sandbox.paypal.com"   # sandbox = fake money

def get_token():
    # Trade Client ID + Secret for a temporary access token
    r = httpx.post(f"{BASE}/v1/oauth2/token",
        auth=(os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_CLIENT_SECRET"]),
        data={"grant_type": "client_credentials"})
    r.raise_for_status()            # stops with an error if keys are wrong
    return r.json()["access_token"]

def test_payout(token):
    # Send $1 from your merchant account to the Trusted Vendor
    r = httpx.post(f"{BASE}/v1/payments/payouts",
        headers={"Authorization": f"Bearer {token}"},
        json={
          "sender_batch_header": {
              "sender_batch_id": str(uuid.uuid4()),   # must be unique per call
              "email_subject": "Test payout"},
          "items": [{
              "recipient_type": "EMAIL",
              "receiver": os.environ["TRUSTED_VENDOR_EMAIL"],
              "amount": {"value": "1.00", "currency": "USD"}}]
        })
    print(r.status_code, r.text)

token = get_token()
print("Auth OK")
test_payout(token)