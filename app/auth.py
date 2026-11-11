import hashlib
import hmac
import secrets
import time

from fastapi import Cookie, Header, HTTPException

from app import config

COOKIE = "guard_session"
TTL = 8 * 3600   # 8 hours

def _sign(expiry: str) -> str:
    return hmac.new(config.ADMIN_TOKEN.encode(), expiry.encode(), hashlib.sha256).hexdigest()

def make_session() -> str:
    expiry = str(int(time.time()) + TTL)
    return f"{expiry}.{_sign(expiry)}"            # "expiry.signature"

def valid_session(value: str) -> bool:
    try:
        expiry, sig = value.split(".", 1)
        return int(expiry) > time.time() and hmac.compare_digest(sig, _sign(expiry))
    except ValueError:
        return False

def token_ok(token: str) -> bool:
    return secrets.compare_digest(token.encode(), config.ADMIN_TOKEN.encode())

def is_admin(session: str, token: str) -> bool:
    return valid_session(session) or token_ok(token)

def require_admin(guard_session: str = Cookie(default=""),
                  x_admin_token: str = Header(default="")):
    if not is_admin(guard_session, x_admin_token):
        raise HTTPException(status_code=401, detail="Admin login required")