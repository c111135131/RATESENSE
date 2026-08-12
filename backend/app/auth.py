"""Minimal admin authentication.

This is intentionally NOT a general-purpose auth system: there is exactly
one admin account, configured via the ADMIN_USERNAME / ADMIN_PASSWORD
environment variables. The defaults below are for local development ONLY
-- set real values via environment variables before deploying anywhere
reachable by other people.

Design note: FastAPI's built-in `HTTPBasic` security scheme sends a
`WWW-Authenticate: Basic` header on a 401, which makes the BROWSER pop up
its own native username/password dialog. That clashes badly with a custom
login page in the SPA. So instead:

  1. POST /api/v1/admin/login with {username, password} in the body.
  2. On success, the backend returns a static opaque token (a hash of the
     configured credentials + a secret salt).
  3. The frontend stores that token (sessionStorage) and sends it back as
     a custom `X-Admin-Token` header on every other /admin/* request.

The token is not time-limited (no real "session" or expiry) -- acceptable
for a single-operator internal tool, but callers should still keep
ADMIN_PASSWORD/ADMIN_TOKEN_SECRET private, and should serve the admin page
over HTTPS in any real deployment.
"""
import hashlib
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, status

# Delete the default value (username, pw, token), when the website is published
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adapt-admin-2026")
ADMIN_TOKEN_SECRET = os.environ.get("ADMIN_TOKEN_SECRET", "adapt-static-salt-change-me")


def _compute_token() -> str:
    raw = f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}:{ADMIN_TOKEN_SECRET}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_login(username: str, password: str) -> Optional[str]:
    """Returns the admin token if username/password match, else None."""
    valid_username = hmac.compare_digest(username, ADMIN_USERNAME)
    valid_password = hmac.compare_digest(password, ADMIN_PASSWORD)
    if valid_username and valid_password:
        return _compute_token()
    return None


def require_admin(x_admin_token: str = Header(default="")) -> None:
    """FastAPI dependency: raises 401 unless X-Admin-Token matches the
    token issued by POST /api/v1/admin/login. Add this as a dependency on
    every admin-only route."""
    if not x_admin_token or not hmac.compare_digest(x_admin_token, _compute_token()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid admin token.",
        )
