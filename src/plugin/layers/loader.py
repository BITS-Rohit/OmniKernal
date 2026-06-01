from src.omni_logger import omni_logger
from src.packet.contracts import CommandManifest, PluginManifest


class PluginEngine:
    """
    Main orchestrator for plugin lifecycle.
    Handles plugins loading & validation

    Args:
        repo:          The OmniRepository to register plugins/tools into.
        plugins_dir:   Directory to scan for plugin folders.
    """

    def __init__(self, repo: OmniRepository, plugins_dir: str):
        self.repo = repo
        self.plugins_dir = plugins_dir
        self.logger = omni_logger.bind(subsystem="plugin_engine")
        self.found_plugins_in_dir: list[str] = []
        self.db_safe_plugins: list[PluginManifest] = []
        self.failed_plugins: list[str] = []
        self.valid_commands: list[CommandManifest] = []
        self._validate_init()

    def _validate_init(self) -> None:
        if self.repo is None:
            raise ValueError("OmniRepository is required for PluginEngine")

        if self.plugins_dir is None:
            raise ValueError("Plugins directory is required for PluginEngine")

        if not os.path.exists(self.plugins_dir):
            raise ValueError(f"Plugins directory not found: {self.plugins_dir}")

    async def discover_and_load(self) -> None:
        """
        Scans the plugins directory and registers valid plugins in the DB.
        """
        self.logger.info(f"Scanning for New plugins in: {self.plugins_dir}")

        for plugin_folder in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, plugin_folder)

            if not os.path.isdir(plugin_path):
                continue
            self.found_plugins_in_dir.append(plugin_folder)
        self.logger.info(f"Found plugins: {len(self.found_plugins_in_dir)}")

        for plugin_folder in self.found_plugins_in_dir:
            plugin_path = os.path.join(self.plugins_dir, plugin_folder)
            plugin: PluginManifest | None = await self._load_plugin(plugin_folder, plugin_path)

            if plugin is None:
                self.failed_plugins.append(plugin_folder)
            else:
                self.db_safe_plugins.append(plugin)

        self.logger.info(f"Valid Plugins to add to DB: {len(self.db_safe_plugins)}")
        if self.failed_plugins:
            self.logger.warning(f"Failed to load plugins: {len(self.failed_plugins)}")

        await self.batch_process()

    async def batch_process(self) -> None:
        await self.repo.register_plugins(self.db_safe_plugins)  # bulk upsert
        await self.repo.register_tools(self.valid_commands)  # bulk upsert

        safe_names = [p.name for p in self.db_safe_plugins]

        if self.failed_plugins:
            await self.repo.remove_plugins(self.failed_plugins)  # bulk delete

        await self.repo.remove_missing_plugins(safe_names)  # bulk delete stale

    def _validate_single_plugin(self, manifest: str, commands: str) -> bool:
        flag = True
        if not os.path.exists(manifest):
            self.logger.debug(f"Manifest not found: {manifest}")
            flag = False
        if not os.path.exists(commands):
            self.logger.debug(f"Commands not found: {commands}")
            flag = False
        return flag

    def _get_dict(self, file: str, is_json: bool) -> dict[str, Any] | None:
        try:
            if is_json:
                with open(file, encoding="utf-8") as f:
                    return cast(dict[str, Any], json.load(f))
            else:
                with open(file, encoding="utf-8") as f:
                    return cast(dict[str, Any], yaml.safe_load(f))
        except UnicodeDecodeError:
            self.logger.debug(f"Wrong encoding (not UTF-8): {file}")

        except PermissionError as e:
            self.logger.debug(f"Permission error: {e}: {file}")
        except OSError as e:
            self.logger.debug(f"OS error: {e}: {file}")

        except Exception as e:
            self.logger.debug(f"Unknown error: {e}: {file}")

        return None

    def _validate_content(
            self, raw: dict[str, Any] | None, commands: dict[str, Any] | None
    ) -> bool:
        if not raw:
            self.logger.debug("Manifest file is empty or contains invalid data")
            return False

        if not commands:
            self.logger.debug("Commands file is empty or contains invalid data")
            return False

        return True

    def _validate_plugin_schema(self, manifest: PluginManifest, plugin_folder: str) -> bool:
        if manifest.name != plugin_folder:
            self.logger.debug(
                f"Plugin load failed for '{plugin_folder}': manifest 'name' ('{manifest.name}') "
                f"does not match folder name. Please rename the folder or fix the manifest."
            )
            return False

        # enforce min_core_version before registration
        if manifest.min_core_version:
            required = _version_tuple(manifest.min_core_version)
            running = _version_tuple(OMNIKERNAL_VERSION)
            if required > running:
                self.logger.warning(
                    f"Plugin '{manifest.name}' requires core v{manifest.min_core_version} "
                    f"but running v{OMNIKERNAL_VERSION}. Skipping. --Suggestion : upgrade plugin version or OmniKernal"
                )
                return False
        return True

    async def _validate_command_schema(
            self, key: str, value: dict[str, str], plugin_name: str
    ) -> CommandManifest | None:
        if not isinstance(value, dict):
            self.logger.debug(
                f"Skipping command '{key}' in plugin '{plugin_name}': Expected a dictionary."
            )
            return None

        pattern = value.get("pattern")
        handler = value.get("handler")
        description = value.get("description", "No description provided")

        if not isinstance(pattern, str) or not isinstance(handler, str):
            self.logger.debug(
                f"Skipping command '{key}' in plugin '{plugin_name}': "
                f"missing or invalid 'pattern' or 'handler'."
            )
            return None

        existing = await self.repo.get_tool_by_command(key)
        if existing and existing.plugin_name != plugin_name:
            self.logger.warning(
                f"Command name conflict: '{key}' is already registered "
                f"by plugin '{existing.plugin_name}'. "
                f"Plugin '{plugin_name}' will overwrite it."
            )

        if minimum_role is not None and not isinstance(minimum_role, str):
            self.logger.debug(
                f"Skipping command '{key}' in plugin '{plugin_name}': "
                f"missing or invalid 'minimum_role'."
            )
            return None

        # Verify that the handler Python file actually exists on disk
        try:
            module_path, func_name = handler.rsplit(".", 1)
            handler_file_path = (
                    os.path.join(self.plugins_dir, plugin_name, *module_path.split(".")) + ".py"
            )
            if not os.path.exists(handler_file_path):
                self.logger.error(
                    f"Handler file missing for '{key}' in plugin '{plugin_name}': {handler_file_path}"
                )
                return None
        except ValueError:
            self.logger.error(
                f"Invalid handler format for '{key}': {handler}. Expected format 'module.func'"
            )
            return None

        command_manifest = CommandManifest(
            name=key,
            description=description,
            pattern=pattern,
            handler=handler,
            plugin_name=plugin_name
        )

        return command_manifest

    async def _load_plugin(self, plugin_folder: str, path: str) -> PluginManifest | None:
        """
        Loads a single plugin folder.

        Returns :
            PluginManifest | None :  PluginManifest object on sucess else None
        """
        manifest_json = os.path.join(path, "manifest.json")
        commands_yaml = os.path.join(path, "commands.yaml")

        if not self._validate_single_plugin(manifest_json, commands_yaml):
            return None

        raw: dict[str, Any] | None = self._get_dict(manifest_json, True)
        commands: dict[str, Any] | None = self._get_dict(commands_yaml, False)

        if not self._validate_content(raw, commands):
            return None

        assert raw is not None
        assert commands is not None

        manifest: PluginManifest = PluginManifest.from_dict(raw)
        try:
            if not self._validate_plugin_schema(manifest, plugin_folder):
                return None

            # Processing Commands from commands.yaml
            invalid_count = 0
            for cmd_name, cmd_info in commands.items():
                if isinstance(cmd_info, dict):
                    cmd: CommandManifest | None = await self._validate_command_schema(
                        cmd_name, cmd_info, manifest.name
                    )
                    if cmd:
                        self.valid_commands.append(cmd)
                    else:
                        invalid_count += 1
                else:
                    self.logger.debug(
                        f"Invalid command format for '{cmd_name}': expected dict, got {type(cmd_info).__name__}"
                    )
                    invalid_count += 1

            self.logger.debug(
                f"Loaded plugin '{manifest.name}' with {len(commands) - invalid_count} valid commands"
            )
            return manifest

        except Exception as e:
            self.logger.debug(f"Failed to load plugin '{plugin_folder}': {e}")
            return None
