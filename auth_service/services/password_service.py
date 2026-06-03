# services/password_service.py
from __future__ import annotations

import hashlib

from services.utils import hash_password, verify_password


class PasswordService:
    def hash_password(self, password: str) -> str:
        return hash_password(password)

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        return verify_password(plain_password, password_hash)

    def hash_token(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    
    def hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()