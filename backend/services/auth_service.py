from __future__ import annotations

"""Purpose: Authentication service for user credentials.

Usage: Creates and verifies user credentials with hashed passwords.

Functions available:
- AuthService.create_credentials, verify_credentials, hash_password, verify_password

Classes available:
- AuthService
"""

import hashlib
import secrets

from sqlalchemy.orm import Session

from backend.repositories import CredentialRepository


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = CredentialRepository(session)

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        hash_value = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return f"{salt}${hash_value.hex()}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        if "$" not in password_hash:
            return False
        salt, stored_hash = password_hash.split("$", 1)
        hash_value = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return hash_value.hex() == stored_hash

    def create_credentials(self, user_id, username: str, password: str) -> None:
        existing = self.repository.get_by_username(username)
        if existing is not None:
            raise ValueError("Username already exists.")
        password_hash = self.hash_password(password)
        self.repository.create(user_id, username, password_hash)

    def verify_credentials(self, username: str, password: str) -> bool:
        cred = self.repository.get_by_username(username)
        if cred is None:
            return False
        return self.verify_password(password, cred.password_hash)
