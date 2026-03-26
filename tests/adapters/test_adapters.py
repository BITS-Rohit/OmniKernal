"""
Tests for AdapterValidator and AdapterLoader.
"""

import pytest
import yaml

from omnikernal.adapters.console_mock import ConsoleMockAdapter
from omnikernal.adapters.loader import AdapterLoader
from omnikernal.adapters.validator import AdapterValidator
from omnikernal.core.interfaces.platform_adapter import PlatformAdapter


class TestAdapterValidator:
    """Tests for class validation (ABC compliance checker)."""

    def setup_method(self):
        self.validator = AdapterValidator()

    def test_valid_descriptor(self, tmp_path):
        desc = {
            "name": "test-adapter",
            "platform": "test",
            "version": "1.0.0",
            "entry_class": "adapter.TestAdapter",
        }
        yaml_file = tmp_path / "adapter.yaml"
        yaml_file.write_text(yaml.dump(desc))

        result = self.validator.validate_descriptor(str(yaml_file))
        assert result["name"] == "test-adapter"
        assert result["platform"] == "test"

    def test_missing_fields_rejected(self, tmp_path):
        desc = {"name": "incomplete"}  # missing platform, version, entry_class
        yaml_file = tmp_path / "adapter.yaml"
        yaml_file.write_text(yaml.dump(desc))

        with pytest.raises(ValueError, match="missing required fields"):
            self.validator.validate_descriptor(str(yaml_file))

    def test_malformed_yaml_rejected(self, tmp_path):
        yaml_file = tmp_path / "adapter.yaml"
        yaml_file.write_text("just a plain string, not a mapping")

        with pytest.raises(ValueError, match="not a valid YAML mapping"):
            self.validator.validate_descriptor(str(yaml_file))

    def test_valid_class_passes(self):
        """ConsoleMockAdapter should pass class validation."""
        self.validator.validate_class(ConsoleMockAdapter)  # Should not raise

    def test_non_subclass_rejected(self):
        class FakeAdapter:
            pass

        with pytest.raises(TypeError, match="must be a subclass"):
            self.validator.validate_class(FakeAdapter)


class TestAdapterLoader:
    """Tests for registry-based adapter loading."""

    def test_register_and_load(self):
        loader = AdapterLoader()
        loader.register("console", ConsoleMockAdapter)
        adapter = loader.load("console")

        assert isinstance(adapter, PlatformAdapter)
        assert adapter.platform_name == "console"

    def test_load_unregistered_raises(self):
        loader = AdapterLoader()
        with pytest.raises(KeyError, match="No adapter registered"):
            loader.load("nonexistent_adapter")

    def test_register_non_adapter_raises(self):
        loader = AdapterLoader()

        class NotAnAdapter:
            pass

        with pytest.raises(TypeError, match="not a PlatformAdapter subclass"):
            loader.register("bad", NotAnAdapter)

    def test_list_adapters(self):
        loader = AdapterLoader()
        loader.register("console", ConsoleMockAdapter)
        adapters = loader.list_adapters()
        assert "console" in adapters

    def test_multiple_registrations(self):
        loader = AdapterLoader()
        loader.register("console", ConsoleMockAdapter)
        loader.register("console2", ConsoleMockAdapter)
        assert set(loader.list_adapters()) == {"console", "console2"}
