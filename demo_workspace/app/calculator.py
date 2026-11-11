"""Mathematical utility functions for financial calculations."""

from typing import List, Union
import math


def add(a: float, b: float) -> float:
    """Returns the sum of two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Returns the difference between two numbers."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Returns the product of two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """Divides a by b.
    
    Raises:
        ValueError: If b is zero.
    """
    if b == 0:
        return a / b  # BUG: Causes ZeroDivisionError rather than expected ValueError
    return a / b


def power(base: float, exponent: float) -> float:
    """Calculates base raised to the power of exponent."""
    return math.pow(base, exponent)


def mean(numbers: List[float]) -> float:
    """Calculates arithmetic mean of a sequence of numbers."""
    if not numbers:
        raise ValueError("Cannot calculate mean of empty list")
    return sum(numbers) / len(numbers)
