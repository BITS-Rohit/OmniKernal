"""Test stubs for PlatformAdapter ABC — structural correctness only."""

from collections.abc import AsyncIterator
from typing import Any, cast

import pytest

from omnikernal.core.contracts.intent_packet import IntentPacket
from omnikernal.core.contracts.message import Message
from omnikernal.core.interfaces.platform_adapter import PlatformAdapter


def test_platform_adapter_is_abstract():
    """PlatformAdapter cannot be instantiated directly — it's an ABC."""
    with pytest.raises(TypeError):
        cast(Any, PlatformAdapter)()


def test_platform_adapter_concrete_missing_methods_raises():
    """A subclass missing abstract methods raises TypeError on instantiation."""

    class IncompleteAdapter(PlatformAdapter):
        pass  # missing all abstract methods

    with pytest.raises(TypeError):
        cast(Any, IncompleteAdapter)()


def test_platform_adapter_full_concrete_instantiates():
    """A fully implemented subclass instantiates without error."""

    class ConcreteAdapter(PlatformAdapter):
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def connect(self) -> bool:
            return True

        async def is_connected(self) -> bool:
            return True

        async def fetch_new_messages(self) -> AsyncIterator[Message]:
            if False:
                yield cast(Message, None)

        async def send_message(self, packet: IntentPacket) -> bool:
            return True

        async def disconnect(self) -> bool:
            return True

        @property
        def platform_name(self) -> str:
            return "mock"

    adapter = ConcreteAdapter()
    assert adapter.platform_name == "mock"

