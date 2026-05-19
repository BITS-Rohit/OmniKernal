"""
Contract for a single command that is defined inside a plugin's commands.yaml
This is used to validate the command against the schema and to create a Command object.
"""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandManifest:
    name : str
    description : str
    pattern : str
    handler : str
    minimum_role : str
    plugin_name : str

