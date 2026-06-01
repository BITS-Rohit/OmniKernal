from src.database.repository import OmniRepository
from src.omni_logger import omni_logger
from src.packet.contracts import CommandManifest, PluginManifest

# single source of truth for the current Core version
OMNIKERNAL_VERSION: str = "0.1.0"

class Validator:
    @staticmethod
    def _validate_init(repo: OmniRepository, plugins_dir: str):
        if repo is None:
            raise ValueError("OmniRepository is required for PluginEngine")

        if plugins_dir is None:
            raise ValueError("Plugins directory is required for PluginEngine")

        if not os.path.exists(plugins_dir):
            raise ValueError(f"Plugins directory not found: {plugins_dir}")

    @staticmethod
    def validate_single_plugin(manifest: str, commands: str) -> bool:
        flag = True
        if not os.path.exists(manifest):
            omni_logger.debug(f"Manifest not found: {manifest}")
            flag = False
        if not os.path.exists(commands):
            omni_logger.debug(f"Commands not found: {commands}")
            flag = False
        return flag

    @staticmethod
    def validate_content(
            raw: dict[str, Any] | None,
            commands: dict[str, Any] | None) -> bool:

        if not raw:
            omni_logger.debug("Manifest file is empty or contains invalid data")
            return False

        if not commands:
            omni_logger.debug("Commands file is empty or contains invalid data")
            return False

        return True

    @staticmethod
    def validate_plugin_schema(manifest: PluginManifest, plugin_folder: str) -> bool:
        if manifest.name != plugin_folder:
            omni_logger.debug(
                f"Plugin load failed for '{plugin_folder}': manifest 'name' ('{manifest.name}') "
                f"does not match folder name. Please rename the folder or fix the manifest."
            )
            return False

        # enforce min_core_version before registration
        if manifest.min_core_version:
            required = _version_tuple(manifest.min_core_version)
            running = _version_tuple(OMNIKERNAL_VERSION)
            if required > running:
                omni_logger.warning(
                    f"Plugin '{manifest.name}' requires core v{manifest.min_core_version} "
                    f"but running v{OMNIKERNAL_VERSION}. Skipping. --Suggestion : upgrade plugin version or OmniKernal"
                )
                return False
        return True

    @staticmethod
    async def validate_command_schema(
            key: str,
            value: dict[str, str],
            plugin_name: str,
            repo : OmniRepository,
            plugins_dir: str
    ) -> CommandManifest | None:
        if not isinstance(value, dict):
            omni_logger.debug(
                f"Skipping command '{key}' in plugin '{plugin_name}': Expected a dictionary."
            )
            return None

        pattern = value.get("pattern")
        handler = value.get("handler")
        description = value.get("description", "No description provided")
        minimum_role = value.get("Minimum_Role", "USER")

        if not isinstance(pattern, str) or not isinstance(handler, str):
            omni_logger.debug(
                f"Skipping command '{key}' in plugin '{plugin_name}': "
                f"missing or invalid 'pattern' or 'handler'."
            )
            return None

        existing = await repo.get_tool_by_command(key)
        if existing and existing.plugin_name != plugin_name:
            omni_logger.warning(
                f"Command name conflict: '{key}' is already registered "
                f"by plugin '{existing.plugin_name}'. "
                f"Plugin '{plugin_name}' will overwrite it."
            )

        if minimum_role is not None and not isinstance(minimum_role, str):
            omni_logger.debug(
                f"Skipping command '{key}' in plugin '{plugin_name}': "
                f"missing or invalid 'minimum_role'."
            )
            return None

        # Verify that the handler Python file actually exists on disk
        try:
            module_path, func_name = handler.rsplit(".", 1)
            handler_file_path = (
                    os.path.join(plugins_dir, plugin_name, *module_path.split(".")) + ".py"
            )
            if not os.path.exists(handler_file_path):
                omni_logger.error(
                    f"Handler file missing for '{key}' in plugin '{plugin_name}': {handler_file_path}"
                )
                return None
        except ValueError:
            omni_logger.error(
                f"Invalid handler format for '{key}': {handler}. Expected format 'module.func'"
            )
            return None

        command_manifest = CommandManifest(
            name=key,
            description=description,
            pattern=pattern,
            handler=handler,
            plugin_name=plugin_name,
        )

        return command_manifest

