from decimal import Decimal
from app import config
from app.models import PaymentRequest, Verdict
from app.policy import evaluate

GOOD = config.TRUSTED_VENDORS["Acme Supplies"]

def req(email=GOOD, amount="50", vendor="Acme Supplies"):
    return PaymentRequest(vendor_name=vendor, payee_email=email, amount=Decimal(amount))

def test_trusted_small_payment_allowed():
    assert evaluate(req()).verdict == Verdict.ALLOW

def test_swapped_payee_blocked():
    assert evaluate(req(email="scammer@example.com")).verdict == Verdict.BLOCK

def test_large_payment_needs_approval():
    assert evaluate(req(amount="500")).verdict == Verdict.NEEDS_APPROVAL