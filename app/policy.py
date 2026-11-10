from app import config
from app.models import Decision, PaymentRequest, RuleResult, Verdict
from typing import Optional

SEVERITY = {Verdict.ALLOW: 0, Verdict.NEEDS_APPROVAL: 1, Verdict.BLOCK: 2}

def check_payee(req: PaymentRequest, vendor: Optional[dict]) -> RuleResult:
    if vendor is None:
        return RuleResult(rule="payee_check", verdict=Verdict.NEEDS_APPROVAL,
                          reason=f"New vendor '{req.vendor_name}' is not on the allowlist")
    if vendor["payee_email"].lower() != req.payee_email.lower():
        return RuleResult(rule="payee_check", verdict=Verdict.BLOCK,
                          reason="Payee email does not match the one on file (possible fraud)")
    return RuleResult(rule="payee_check", verdict=Verdict.ALLOW, reason="Known vendor, payee matches")


def check_hard_limit(req: PaymentRequest) -> RuleResult:
    if req.amount > config.MAX_SINGLE_PAYMENT:
        return RuleResult(rule="hard_limit", verdict=Verdict.BLOCK,
                          reason=f"Amount exceeds the maximum of {config.MAX_SINGLE_PAYMENT}")
    return RuleResult(rule="hard_limit", verdict=Verdict.ALLOW, reason="Within hard limit")

def check_approval_threshold(req: PaymentRequest) -> RuleResult:
    if req.amount > config.APPROVAL_THRESHOLD:
        return RuleResult(rule="approval_threshold", verdict=Verdict.NEEDS_APPROVAL,
                          reason=f"Amount above {config.APPROVAL_THRESHOLD} needs human approval")
    return RuleResult(rule="approval_threshold", verdict=Verdict.ALLOW, reason="Below approval threshold")

RULES = [check_hard_limit, check_approval_threshold]

def evaluate(req: PaymentRequest, vendor: Optional[dict] = None, extra=()) -> Decision:
    results = [check_payee(req, vendor), *[rule(req) for rule in RULES], *extra]
    worst = max(results, key=lambda r: SEVERITY[r.verdict])       # worst verdict wins
    reasons = [r.reason for r in results if r.verdict != Verdict.ALLOW] or ["All checks passed"]
    return Decision(verdict=worst.verdict, reasons=reasons, results=results)