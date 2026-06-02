"""Test stubs for Message contract — construction and immutability."""

from datetime import datetime
from typing import Any, cast

import pytest
from pydantic import ValidationError

from src.packet.contracts.message import Message
from src.packet.contracts.user import User


def _make_user() -> User:
    return User(id="u1", display_name="Alice", platform="whatsapp")


def _make_message(id: str = "m1", raw_text: str = "!echo hello") -> Message:
    """Helper: build a Message via model_validate to bypass Pydantic nested re-validation."""
    ts = datetime(2026, 3, 1, 12, 0, 0)
    return Message.model_validate(
        {
            "id": id,
            "raw_text": raw_text,
            "user": _make_user(),
            "timestamp": ts,
            "platform": "whatsapp",
        }
    )


def test_message_construction():
    msg = _make_message()
    assert msg.id == "m1"
    assert msg.raw_text == "!echo hello"
    assert msg.platform == "whatsapp"
    assert msg.timestamp == datetime(2026, 3, 1, 12, 0, 0)


def test_message_is_immutable():
    msg = _make_message(id="m2", raw_text="test")
    with pytest.raises((ValidationError, TypeError)):
        cast(Any, msg).raw_text = "tampered"


def test_message_repr_truncates_long_text():
    msg = _make_message(id="m3", raw_text="a" * 100)
    assert "..." in repr(msg)
