import base64
import hashlib
import hmac
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import JWT_SECRET, TOKEN_HOURS
from .db import get_db

ITERATIONS = 240_000
_bearer = HTTPBearer(auto_error=False)


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, digest = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(iters))
        return hmac.compare_digest(dk, base64.b64decode(digest))
    except Exception:
        return False


def _encode(payload: dict, minutes: int) -> str:
    payload = {**payload, "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def create_access_token(user_id: int) -> str:
    return _encode({"sub": str(user_id), "typ": "access"}, TOKEN_HOURS * 60)


def _pw_fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:12]


def create_reset_token(user_id: int, password_hash: str) -> str:
    # Bound to the current password hash, so the link stops working once used.
    return _encode({"sub": str(user_id), "typ": "reset", "fp": _pw_fingerprint(password_hash)}, 30)


def read_reset_token(token: str, db: sqlite3.Connection):
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if data.get("typ") != "reset":
        return None
    user = db.execute("SELECT * FROM users WHERE id=?", (int(data["sub"]),)).fetchone()
    if not user or _pw_fingerprint(user["password_hash"]) != data.get("fp"):
        return None
    return user


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                 db: sqlite3.Connection = Depends(get_db)) -> sqlite3.Row:
    if not creds:
        raise HTTPException(401, "Please sign in to continue.")
    try:
        data = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
        if data.get("typ") != "access":
            raise jwt.InvalidTokenError()
    except jwt.PyJWTError:
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    user = db.execute("SELECT * FROM users WHERE id=?", (int(data["sub"]),)).fetchone()
    if not user:
        raise HTTPException(401, "Account not found. Please sign in again.")
    return user
