"""Test stubs for User contract — construction and immutability."""

from typing import Any, cast

import pytest
from pydantic import ValidationError

from src.packet.contracts.user import ROLE, User


def test_user_construction():
    u = User(id="123", display_name="Alice", platform="whatsapp")
    assert u.id == "123"
    assert u.display_name == "Alice"
    assert u.platform == "whatsapp"
    assert u.role == ROLE.USER  # default


def test_user_admin_role():
    u = User(id="1", display_name="Admin", platform="whatsapp", role=ROLE.ADMIN)
    assert u.is_admin is True


def test_user_default_not_admin():
    u = User(id="2", display_name="Bob", platform="whatsapp")
    assert u.is_admin is False


def test_user_is_immutable():
    u = User(id="3", display_name="Carol", platform="whatsapp")
    with pytest.raises((ValidationError, TypeError)):
        cast(Any, u).display_name = "Changed"
