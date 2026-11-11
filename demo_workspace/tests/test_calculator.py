"""Unit test suite for calculator module."""

import pytest
import sys
import os

# Ensure demo_workspace root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.calculator import add, subtract, multiply, divide, power, mean


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_subtract():
    assert subtract(10, 4) == 6


def test_multiply():
    assert multiply(3, 7) == 21


def test_divide_valid():
    assert divide(10, 2) == 5.0


def test_divide_by_zero():
    """Verify that dividing by zero raises ValueError with descriptive message."""
    with pytest.raises(ValueError, match="Division by zero is undefined"):
        divide(10, 0)


def test_mean():
    assert mean([2, 4, 6]) == 4.0
