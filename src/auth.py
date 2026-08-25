"""Admin authentication for the web app.

Admins live in the `admins` collection of the same MongoDB database
({_id: username, password_hash, created_at}). There is no self-registration:
accounts are added via `python -m src.manage_admins add <username>` (or
inserted manually into the DB).

Login issues a signed JWT (PyJWT) that the React app sends as
`Authorization: Bearer <token>`. The token carries the username and expires
after TOKEN_TTL_HOURS.
"""

import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import jsonify, request

from src.database import get_db

TOKEN_TTL_HOURS = 12


def get_secret_key():
    key = os.getenv("SECRET_KEY", "")
    if not key:
        raise RuntimeError("SECRET_KEY is not set. Add it to .env (a random hex string).")
    return key


# --- password hashing (bcrypt) ---

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# --- admin CRUD ---

def admins_collection():
    return get_db().admins


def create_admin(username, password):
    if not username or not password:
        raise ValueError("username and password are required")
    username = username.strip()
    doc = {
        "_id": username,
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc),
    }
    admins_collection().replace_one({"_id": username}, doc, upsert=True)
    return username


def remove_admin(username):
    result = admins_collection().delete_one({"_id": username})
    return result.deleted_count > 0


def list_admins():
    return [doc["_id"] for doc in admins_collection().find({}, {"_id": 1})]


def verify_admin(username, password):
    doc = admins_collection().find_one({"_id": username})
    if doc is None:
        return False
    return verify_password(password, doc.get("password_hash", ""))


# --- JWT ---

def create_token(username):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, get_secret_key(), algorithm="HS256")


def decode_token(token):
    return jwt.decode(token, get_secret_key(), algorithms=["HS256"])


def get_current_username():
    """Return the username from the Authorization header, or None."""
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    try:
        return decode_token(token).get("sub")
    except jwt.PyJWTError:
        return None


def require_auth(func):
    """Flask decorator: reject requests without a valid bearer token."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        username = get_current_username()
        if username is None:
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return wrapper
