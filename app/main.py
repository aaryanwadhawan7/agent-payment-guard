import secrets
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from fastapi.staticfiles import StaticFiles

import httpx
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Response, Query
from fastapi.responses import FileResponse

from app import auth, config, injection, notify, paypal_client, policy, service, store, notify, demo, service
from app.models import PayResponse, PaymentRequest, Verdict, VendorIn, LoginIn

STATIC = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()          # create the table on startup
    for name, email in config.TRUSTED_VENDORS.items():   # demo vendor seeded once
        store.add_vendor(name, email)
    yield

app = FastAPI(title="Agent Payment Guard", version="0.2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.include_router(demo.router)

@app.get("/")
def dashboard():
    return FileResponse(STATIC / "index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/pay", response_model=PayResponse)
def pay(req: PaymentRequest):
    return service.process_payment(req)

@app.get("/decisions")
def decisions():
    return store.list_entries()

@app.post("/decisions/{decision_id}/approve", dependencies=[Depends(auth.require_admin)])
def approve(decision_id: int, trust: bool = False):
    row = store.get(decision_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    if not store.claim_pending(decision_id):
        raise HTTPException(status_code=409, detail=f"Cannot approve: status is '{row['status']}'")
    req = PaymentRequest(vendor_name=row["vendor_name"], payee_email=row["payee_email"],
                         amount=Decimal(row["amount"]), currency=row["currency"],
                         note=row["note"])
    try:
        batch_id = paypal_client.send_payout(req)
    except httpx.HTTPError:
        store.set_status(decision_id, "pending")      # put it back so it can be retried
        raise HTTPException(status_code=502, detail="PayPal request failed")
    store.set_status(decision_id, "paid", batch_id)
    if trust:                                            # onboard this vendor
        store.add_vendor(row["vendor_name"], row["payee_email"])
    return {"decision_id": decision_id, "status": "paid", "payout_batch_id": batch_id}

@app.post("/decisions/{decision_id}/reject", dependencies=[Depends(auth.require_admin)])
def reject(decision_id: int):
    if not store.reject_pending(decision_id):
        raise HTTPException(status_code=409, detail="Only pending decisions can be rejected")
    return {"decision_id": decision_id, "status": "rejected"}

@app.get("/vendors")
def vendors():
    return store.list_vendors()

@app.post("/vendors", dependencies=[Depends(auth.require_admin)])
def create_vendor(v: VendorIn):
    if not store.add_vendor(v.name, v.payee_email):
        raise HTTPException(status_code=409, detail="Vendor already exists")
    return store.get_vendor(v.name)

@app.post("/auth/login")
def login(body: LoginIn, response: Response):
    if not auth.token_ok(body.token):
        raise HTTPException(status_code=401, detail="Wrong admin token")
    response.set_cookie(auth.COOKIE, auth.make_session(), max_age=auth.TTL,
                        httponly=True, samesite="strict",
                        secure=config.PUBLIC_URL.startswith("https"))
    return {"admin": True}

@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(auth.COOKIE)
    return {"admin": False}

@app.get("/auth/me")
def me(guard_session: str = Cookie(default=""), x_admin_token: str = Header(default="")):
    return {"admin": auth.is_admin(guard_session, x_admin_token)}

@app.get("/decisions")
def decisions(limit: int = Query(200, ge=1, le=500)):
    return store.list_entries(limit)