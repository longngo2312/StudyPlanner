#app/routes/auth.py
#register / login / logout with opaque bearer tokens stored in SQLite
#passwords: salted scrypt (stdlib). tokens: random, only their sha256 is stored, expire after TOKEN_DAYS

import hashlib
import hmac
import secrets
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.db import db
from app.models import Credentials, Token, User

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)   #auto_error off so we can return 401 instead of 403
TOKEN_DAYS = 7

def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    """Dependency: resolves the bearer token to a user or raises 401."""
    if creds is None:
        raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    with db() as conn:
        row = conn.execute(
            """SELECT u.id, u.username FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ? AND s.created_at > datetime('now', ?)""",
            (_hash_token(creds.credentials), f"-{TOKEN_DAYS} days")).fetchone()
    if row is None:
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    return User(**dict(row))

@router.post("/register", response_model=User, status_code=201)
def register(c: Credentials):
    salt = secrets.token_bytes(16)
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?)",
                (c.username, salt.hex(), _hash_password(c.password, salt)))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Username already taken")
        return User(id=cur.lastrowid, username=c.username)

@router.post("/login", response_model=Token)
def login(c: Credentials):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (c.username,)).fetchone()
        if row is None or not hmac.compare_digest(
                row["password_hash"], _hash_password(c.password, bytes.fromhex(row["salt"]))):
            raise HTTPException(401, "Wrong username or password")
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions (token_hash, user_id) VALUES (?, ?)",
                     (_hash_token(token), row["id"]))
    return Token(access_token=token)

@router.post("/logout", status_code=204)
def logout(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
           user: User = Depends(current_user)):
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(creds.credentials),))
    return Response(status_code=204)

@router.get("/me", response_model=User)
def me(user: User = Depends(current_user)):
    return user
