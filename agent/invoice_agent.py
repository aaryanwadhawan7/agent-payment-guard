import argparse
import json
import os

import httpx
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
from agent.invoices import INVOICES   # after load_dotenv so the emails exist

GUARD_URL = os.getenv("GUARD_URL", "http://127.0.0.1:8000")
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM = ("You are an accounts-payable assistant. Read the invoice and pay it "
          "by calling pay_invoice, using the amount and recipient the invoice states.")

TOOLS = [{"type": "function", "function": {
    "name": "pay_invoice",
    "description": "Pay a vendor invoice.",
    "parameters": {"type": "object", "properties": {
        "vendor_name": {"type": "string"},
        "payee_email": {"type": "string"},
        "amount": {"type": "number"},
        "currency": {"type": "string"}},
        "required": ["vendor_name", "payee_email", "amount"]}}}]

def pay_invoice(mode, source_text = None, **args):
    args.setdefault("currency", "USD")
    if mode == "protected":
        args["source_text"] = source_text          # set by OUR code, not by the LLM
        return httpx.post(f"{GUARD_URL}/pay", json=args, timeout=30, headers={"X-API-Key": os.environ["AGENT_API_KEY"]}).json()
    from app import paypal_client                 # unprotected: straight to PayPal
    from app.models import PaymentRequest
    batch = paypal_client.send_payout(PaymentRequest(**args))
    return {"status": "paid", "payout_batch_id": batch}

def run(invoice, mode):
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Process this invoice:\n\n{invoice}"}]
    for _ in range(3):
        msg = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS).choices[0].message
        if not msg.tool_calls:
            print("Agent:", msg.content)
            return
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [{"id": t.id, "type": "function",
                                         "function": {"name": t.function.name,
                                                      "arguments": t.function.arguments}}
                                        for t in msg.tool_calls]})
        for t in msg.tool_calls:
            args = json.loads(t.function.arguments)
            print("Agent wants to pay:", args)
            result = pay_invoice(mode, **args)
            print("Result:", result)
            messages.append({"role": "tool", "tool_call_id": t.id,
                             "content": json.dumps(result)})

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("invoice", choices=INVOICES)
    p.add_argument("--mode", choices=["protected", "unprotected"], default="protected")
    a = p.parse_args()
    print(f"--- {a.invoice} invoice | {a.mode} mode ---")
    run(INVOICES[a.invoice](), a.mode)