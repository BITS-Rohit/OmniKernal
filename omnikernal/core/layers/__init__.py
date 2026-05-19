"""
    Layers Order :
    1. resolve cmd name from cache.
    2. User Role Permissions.
    3. maps exe.run process.
    4. Sanitize the packet.
    5. parse the sanitized_text to create cli based headers and vals and store in packet.
    6. execute the mapped func and update the result field in the packet.
    7. Response back to user(using adapter's send_message() method), sends `reply` content to user.
    8. If failed any process , Routed to Hitory or watch Dog for later inspection.
"""

from .execution import ExecutionLayer
from .mapping import MappingLayer
from .parser import Parser
from .response import ResponseLayer
from .sanitizer import CommandSanitizer

__all__ = ["ExecutionLayer", "MappingLayer", "Parser", "CommandSanitizer", "ResponseLayer"]
