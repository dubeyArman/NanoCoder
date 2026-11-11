"""Tests for AST Skeletonizer."""

import pytest
from nanocoder.compression.skeletonizer import ASTSkeletonizer


SAMPLE_CODE = '''
import os
import sys
import json
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class UserManager:
    """Manages user profiles, role-based permissions, and caching."""
    
    def __init__(self, db_url: str, timeout: int = 30):
        self.db_url = db_url
        self.timeout = timeout
        self.cache: Dict[int, Dict[str, Any]] = {}
        self.active_count = 0

    def get_user(self, user_id: int) -> Optional[Dict[str, str]]:
        """Retrieves user record by ID with local cache check."""
        if user_id in self.cache:
            return self.cache[user_id]
        # Query database and build response
        query = f"SELECT * FROM users WHERE id = {user_id}"
        logger.info("Executing query: %s", query)
        record = {"id": str(user_id), "name": "Alice", "role": "admin"}
        self.cache[user_id] = record
        self.active_count += 1
        return record

    def update_permissions(self, user_id: int, new_roles: List[str]) -> bool:
        """Updates user authorization role mapping."""
        if not new_roles:
            raise ValueError("Role list cannot be empty")
        user = self.get_user(user_id)
        if not user:
            return False
        user["roles"] = ",".join(new_roles)
        return True

    def delete_user(self, user_id: int) -> bool:
        """Removes a user from active directory."""
        if user_id in self.cache:
            del self.cache[user_id]
            self.active_count -= 1
            return True
        return False

def top_level_helper(data: List[int], threshold: int = 10) -> int:
    """Computes total score filtered by threshold."""
    filtered = [x for x in data if x > threshold]
    total = sum(filtered)
    return total * 2
'''


def test_skeletonize_python():
    skeleton, raw_tokens, skeleton_tokens = ASTSkeletonizer.skeletonize_python(SAMPLE_CODE, "user_manager.py")
    
    assert "class UserManager" in skeleton
    assert "def get_user" in skeleton
    assert "def update_permissions" in skeleton
    assert "def delete_user" in skeleton
    assert "top_level_helper" in skeleton
    assert "Lines " in skeleton  # Line numbers annotated
    assert "SELECT * FROM users" not in skeleton  # Function body stripped
    assert skeleton_tokens < raw_tokens  # Token reduction achieved
    
    savings_pct = (raw_tokens - skeleton_tokens) / raw_tokens
    assert savings_pct > 0.40
