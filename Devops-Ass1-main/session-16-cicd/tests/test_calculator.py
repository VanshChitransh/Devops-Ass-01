import pytest

from app.calculator import add, calculate, divide, multiply, power, subtract


def test_add():
    assert add(10, 5) == 15


def test_subtract():
    assert subtract(10, 5) == 5


def test_multiply():
    assert multiply(2, 8) == 16


def test_divide():
    assert divide(9, 3) == 3


def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(1, 0)


def test_power():
    assert power(2, 3) == 8


def test_calculate_expression():
    assert calculate("7 - 2") == 5
    assert calculate("2 ^ 10") == 1024
