from typing import Optional 
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum

class Verdict(str, Enum):
    ALLOW = "allow"
    NEEDS_APPROVAL = "needs_approval"
    BLOCK = "block"

class PaymentRequest(BaseModel):          # what the AI agent sends us
    vendor_name: str = Field(min_length=1, max_length=100)
    payee_email: str = Field(min_length=3, max_length=254)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")
    note: Optional[str] = Field(default=None, max_length=500)

class RuleResult(BaseModel):              # one rule's opinion
    rule: str
    verdict: Verdict
    reason: str

class Decision(BaseModel):                # final outcome
    verdict: Verdict
    reasons: list[str]
    results: list[RuleResult]

class PayResponse(BaseModel):             # what we send back
    decision_id: int
    verdict: Verdict
    reasons: list[str]
    payout_batch_id: Optional[str] = None