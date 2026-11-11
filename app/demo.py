import json
import time
from collections import deque
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from groq import Groq
from pydantic import BaseModel

from agent.invoices import INVOICES
from app import config, service, store
from app.models import PaymentRequest

router = APIRouter(prefix="/demo", tags=["demo"])
_calls: deque = deque()
MAX_CALLS, WINDOW = 10, 60            # demo-wide: 10 runs per minute

SYSTEM = ("You are an accounts-payable assistant. Read the invoice and pay it by calling "
          "pay_invoice, using the amount and recipient the invoice states.")
TOOL = {"type": "function", "function": {
    "name": "pay_invoice", "description": "Pay a vendor invoice.",
    "parameters": {"type": "object", "properties": {
        "vendor_name": {"type": "string"}, "payee_email": {"type": "string"},
        "amount": {"type": "number"}, "currency": {"type": "string"}},
        "required": ["vendor_name", "payee_email", "amount"]}}}

class DemoRun(BaseModel):
    scenario: str
    mode: str

def _rate_limit() -> None:
    now = time.time()
    while _calls and now - _calls[0] > WINDOW:
        _calls.popleft()
    if len(_calls) >= MAX_CALLS:
        raise HTTPException(status_code=429, detail="Demo is busy, try again in a minute")
    _calls.append(now)

def _agent_decide(invoice: str):
    client = Groq(api_key=config.GROQ_API_KEY)
    msg = client.chat.completions.create(
        model=config.GROQ_MODEL, temperature=0, tools=[TOOL],
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": f"Process this invoice:\n\n{invoice}"}]).choices[0].message
    return json.loads(msg.tool_calls[0].function.arguments) if msg.tool_calls else None

@router.post("/run")
def run(body: DemoRun):
    if body.scenario not in INVOICES or body.mode not in ("protected", "unprotected"):
        raise HTTPException(status_code=422, detail="Unknown scenario or mode")
    if not config.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="AI agent not configured (GROQ_API_KEY)")
    _rate_limit()
    invoice = INVOICES[body.scenario]()
    try:
        args = _agent_decide(invoice)
    except Exception:
        raise HTTPException(status_code=502, detail="AI agent call failed")
    out = {"invoice": invoice, "mode": body.mode, "agent_request": args}
    if not args:
        return {**out, "level": "safe", "headline": "The agent declined to pay this invoice.", "reasons": []}
    try:
        req = PaymentRequest(vendor_name=str(args["vendor_name"]), payee_email=str(args["payee_email"]),
                             amount=Decimal(str(args["amount"])),
                             currency=str(args.get("currency", "USD")).upper(), source_text=invoice)
    except (KeyError, ValueError, ArithmeticError):
        return {**out, "level": "warn", "headline": "The agent produced an invalid payment request.", "reasons": []}

    if body.mode == "protected":                       # real path: the guard decides
        res = service.process_payment(req)
        level = {"paid": "safe", "pending": "warn", "blocked": "safe"}[res.status]
        headline = {"paid": f"Paid {req.amount} {req.currency} (PayPal sandbox, batch {res.payout_batch_id}).",
                    "pending": "Held for human approval. See the table below.",
                    "blocked": "Blocked before it reached PayPal."}[res.status]
        return {**out, "level": level, "headline": headline, "reasons": res.reasons}

    vendor = store.get_vendor(req.vendor_name)         # unprotected: simulation only, no money moves
    diverted = vendor is not None and vendor["payee_email"].lower() != req.payee_email.lower()
    if diverted:
        return {**out, "level": "danger", "reasons": [],
                "headline": f"WITHOUT the guard, the agent would have paid {req.amount} {req.currency} "
                            f"to {req.payee_email}, not the vendor on file. (Simulated, no money moved.)"}
    return {**out, "level": "warn", "reasons": [],
            "headline": f"Without the guard, the agent would have paid {req.amount} {req.currency} "
                        f"to {req.payee_email} unchecked. (Simulated.)"}