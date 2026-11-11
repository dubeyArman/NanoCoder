"""Tests for Output Distiller."""

import pytest
from nanocoder.compression.output_distiller import OutputDistiller


PYTEST_FAILURE_OUTPUT = """
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.2.0, pluggy-1.7.0
rootdir: F:\\GLOBAL AI HACKATHON\\demo_workspace
collected 6 items

tests/test_calculator.py ....F.                                          [100%]

================================== FAILURES ===================================
_____________________________ test_divide_by_zero _____________________________

    def test_divide_by_zero():
        with pytest.raises(ValueError, match="Division by zero is undefined"):
>           divide(10, 0)

tests/test_calculator.py:32: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

a = 10, b = 0

    def divide(a: float, b: float) -> float:
        if b == 0:
>           return a / b
E           ZeroDivisionError: float division by zero

app/calculator.py:27: ZeroDivisionError
=========================== short test summary info ===========================
FAILED tests/test_calculator.py::test_divide_by_zero - ZeroDivisionError: float division by zero
========================= 1 failed, 5 passed in 0.08s =========================
"""


def test_distill_pytest_output():
    distilled, raw_tokens, distilled_tokens = OutputDistiller.distill_pytest_output(PYTEST_FAILURE_OUTPUT)
    
    assert "FAILURES DETECTED" in distilled
    assert "test_divide_by_zero" in distilled
    assert "ZeroDivisionError" in distilled
    assert "platform win32" not in distilled  # Boilerplate removed
    assert distilled_tokens < raw_tokens
    
    # Check that savings exceed 50%
    savings = (raw_tokens - distilled_tokens) / raw_tokens
    assert savings > 0.50
