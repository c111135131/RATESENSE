import hashlib
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, status

# Delete the default value (username, pw, token), when the website is published
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
ADMIN_TOKEN_SECRET = os.environ.get("ADMIN_TOKEN_SECRET")


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
