"""Authentication and token verification manager."""

from typing import Dict, Optional, Any
import time


class AuthManager:
    """Manages user sessions, password validation, and token signing."""

    def __init__(self, secret_key: str = "production-secret"):
        self.secret_key = secret_key
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def login(self, username: str, password_hash: str) -> Optional[str]:
        """Authenticates user and returns session token."""
        if username == "admin" and password_hash == "hash_admin_123":
            token = f"token_{username}_{int(time.time())}"
            self.active_sessions[token] = {
                "user": username,
                "role": "admin",
                "created_at": time.time()
            }
            return token
        return None

    def verify_token(self, token: Optional[str]) -> bool:
        """Verifies if the provided session token is valid and active."""
        if not token:
            return False
        return token in self.active_sessions
