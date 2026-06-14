import base64
import hashlib
import hmac
import json
import os
import secrets
import time

# in-process secret: daemon and Odoo controllers share the same Python process,
# so they see the same module-level value. MCP subprocesses NEVER need this —
# they just forward whatever signed token the daemon hands them.
_secret: str = os.environ.get("ERP_AGENT_GATEWAY_SECRET") or secrets.token_urlsafe(32)
_DEFAULT_TTL_SECONDS = 60


def secret() -> str:
    return _secret


def sign(payload: dict, ttl: int = _DEFAULT_TTL_SECONDS) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + ttl
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(_secret.encode("utf-8"), raw, hashlib.sha256).digest()
    return (
        base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        + "."
        + base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    )


def verify(token: str) -> dict | None:
    try:
        body_b64, sig_b64 = token.split(".", 1)
        raw = base64.urlsafe_b64decode(body_b64 + "=" * (-len(body_b64) % 4))
        sig = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
    except Exception:
        return None
    expected = hmac.new(_secret.encode("utf-8"), raw, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload
