"""Unit test suite for auth manager."""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import AuthManager


def test_login_success():
    auth = AuthManager()
    token = auth.login("admin", "hash_admin_123")
    assert token is not None
    assert auth.verify_token(token) is True


def test_login_failure():
    auth = AuthManager()
    token = auth.login("admin", "wrong_hash")
    assert token is None


def test_verify_empty_token():
    auth = AuthManager()
    assert auth.verify_token(None) is False
    assert auth.verify_token("") is False
