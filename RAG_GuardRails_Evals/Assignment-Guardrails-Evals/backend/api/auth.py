"""
auth.py - Authentication: login, JWT token generation, user management
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

try:
    from jose import JWTError, jwt as _jwt_lib
    def _jwt_encode(data: dict, key: str, algorithm: str) -> str:
        return _jwt_lib.encode(data, key, algorithm=algorithm)
    def _jwt_decode(token: str, key: str, algorithms: list) -> dict:
        return _jwt_lib.decode(token, key, algorithms=algorithms)
    _JWTError = JWTError
except ImportError:
    import json, base64, hmac, hashlib, time
    _JWTError = Exception  # type: ignore
    def _jwt_encode(data: dict, key: str, algorithm: str) -> str:  # type: ignore
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps(data, default=str).encode()).rstrip(b"=")
        sig = hmac.new(key.encode(), header + b"." + payload, hashlib.sha256).digest()
        return (header + b"." + payload + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
    def _jwt_decode(token: str, key: str, algorithms: list) -> dict:  # type: ignore
        parts = token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        exp = payload.get("exp")
        if exp and time.time() > exp:
            raise Exception("Token expired")
        return payload

try:
    import bcrypt as _bcrypt
    def _hash_password(plain: str) -> str:
        return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()
    def _verify_password(plain: str, hashed: str) -> bool:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
except Exception:
    import hashlib, hmac, os, base64
    def _hash_password(plain: str) -> str:
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 260000)
        return base64.b64encode(salt + dk).decode()
    def _verify_password(plain: str, hashed: str) -> bool:
        raw = base64.b64decode(hashed.encode())
        salt, dk = raw[:16], raw[16:]
        dk2 = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 260000)
        return hmac.compare_digest(dk, dk2)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings, DEMO_USERS, ADMIN_USER, RBAC_MATRIX
from api.models import LoginRequest, TokenResponse, UserInfo
from guardrails.input_guards import reset_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# In-memory user store (seeded from config)
_users: dict[str, dict] = {}


def _init_users():
    global _users
    for username, user_data in DEMO_USERS.items():
        _users[username] = {
            "username": username,
            "full_name": user_data["full_name"],
            "role": user_data["role"],
            "department": user_data["department"],
            "hashed_password": _hash_password(user_data["plain_password"]),
        }
    _users["admin"] = {
        "username": "admin",
        "full_name": "System Administrator",
        "role": "c_level",
        "department": "IT",
        "hashed_password": _hash_password(ADMIN_USER["plain_password"]),
        "is_admin": True,
    }
    logger.info(f"Initialized {len(_users)} users")


_init_users()


def get_user(username: str) -> dict | None:
    return _users.get(username)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _verify_password(plain_password, hashed_password)


def authenticate_user(username: str, password: str) -> dict | None:
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return _jwt_encode(to_encode, settings.secret_key, settings.algorithm)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = _jwt_decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except _JWTError:
        raise credentials_exception

    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "c_level" and not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["username"]})
    reset_session(user["username"])
    accessible_collections = RBAC_MATRIX.get(user["role"], [])
    return TokenResponse(
        access_token=access_token,
        username=user["username"],
        full_name=user["full_name"],
        role=user["role"],
        department=user["department"],
        accessible_collections=accessible_collections,
    )


@router.post("/token", response_model=TokenResponse)
async def login_form(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(data={"sub": user["username"]})
    reset_session(user["username"])
    accessible_collections = RBAC_MATRIX.get(user["role"], [])
    return TokenResponse(
        access_token=access_token,
        username=user["username"],
        full_name=user["full_name"],
        role=user["role"],
        department=user["department"],
        accessible_collections=accessible_collections,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserInfo(
        username=current_user["username"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        department=current_user["department"],
        accessible_collections=RBAC_MATRIX.get(current_user["role"], []),
    )


# User management helpers (used by admin API)
def create_user(username: str, full_name: str, role: str, department: str, password: str) -> dict:
    if username in _users:
        raise ValueError(f"User '{username}' already exists")
    _users[username] = {
        "username": username,
        "full_name": full_name,
        "role": role,
        "department": department,
        "hashed_password": _hash_password(password),
    }
    return _users[username]


def update_user(username: str, updates: dict) -> dict:
    if username not in _users:
        raise ValueError(f"User '{username}' not found")
    if "password" in updates:
        updates["hashed_password"] = _hash_password(updates.pop("password"))
    _users[username].update(updates)
    return _users[username]


def delete_user(username: str):
    if username not in _users:
        raise ValueError(f"User '{username}' not found")
    del _users[username]


def list_users() -> list[dict]:
    return list(_users.values())

