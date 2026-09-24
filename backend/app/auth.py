import hmac
import os
from typing import Optional
import time

from fastapi import Header, HTTPException, status
import jwt

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
ADMIN_TOKEN_SECRET = os.environ.get("ADMIN_TOKEN_SECRET")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def _create_admin_token() -> str:
    payload = {
        "sub": ADMIN_USERNAME,
        "exp": int(time.time()) + (ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    }
    return jwt.encode(payload, ADMIN_TOKEN_SECRET, algorithm=JWT_ALGORITHM)


def verify_login(username: str, password: str) -> Optional[str]:
    if not ADMIN_USERNAME or not ADMIN_PASSWORD or not ADMIN_TOKEN_SECRET:
        return None
        
    valid_username = hmac.compare_digest(username, ADMIN_USERNAME)
    valid_password = hmac.compare_digest(password, ADMIN_PASSWORD)
    
    if valid_username and valid_password:
        return _create_admin_token()
    return None

def require_admin(x_admin_token: str = Header(default="")) -> None:
    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin token.",
        )

    try:
        payload = jwt.decode(
            x_admin_token, ADMIN_TOKEN_SECRET, algorithms=[JWT_ALGORITHM]
        )

        if payload.get("sub") != ADMIN_USERNAME:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token scope.",
            )
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid admin token.",
        )
