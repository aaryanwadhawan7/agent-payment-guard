from decimal import Decimal
from app import config, store
from app.models import PaymentRequest
from app.policy import evaluate

def test_pending_can_only_be_claimed_once(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    store.init_db()
    req = PaymentRequest(vendor_name="New Co", payee_email="a@b.com", amount=Decimal("500"))
    decision_id = store.add(req, evaluate(req), "pending")
    assert store.claim_pending(decision_id) is True
    assert store.claim_pending(decision_id) is False   # second approve can't pay again