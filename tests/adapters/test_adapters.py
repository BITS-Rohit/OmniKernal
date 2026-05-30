"""
Tests for AdapterManager and MockAdapter.
"""

from omnikernal.plugin.adapters import AdapterManager, MockAdapter
from omnikernal.plugin.interfaces import PlatformAdapter


class TestAdapterManager:
    """Tests for registry-based adapter manager."""

    def test_register_and_get_primary(self):
        manager = AdapterManager()
        adapter = MockAdapter()
        failed = manager.register("console", adapter)

        assert not failed
        assert manager.get_primary("console") is adapter
        assert isinstance(adapter, PlatformAdapter)
        assert adapter.platform_name == "console"

    def test_register_multiple_instances(self):
        manager = AdapterManager()
        a1 = MockAdapter()
        a2 = MockAdapter()
        failed = manager.register("console", [a1, a2])

        assert not failed
        assert manager.get_primary("console") is a1
        assert manager.list_platforms() == ["console"]

    def test_register_non_adapter_rejects(self):
        manager = AdapterManager()

        class NotAnAdapter:
            pass

        bad_instance = NotAnAdapter()
        failed = manager.register("bad", bad_instance)  # type: ignore[arg-type]
        assert len(failed) == 1
        assert failed[0] is bad_instance
