"""
devkit_error — Layer 6: Error-Path Pipeline Test

Validates: When a handler returns CommandResult.error(), the Core:
  1. Does NOT crash — it catches the error result gracefully
  2. Logs it to the execution_log table (success=False, error_reason set)
  3. Still sends the error reply back via adapter.send_message()
  4. Continues polling — the error doesn't break the event loop

This is the "intentional failure" test. If you receive a reply to this
command, the entire error-handling pipeline is confirmed working.
"""

from src.core.contracts.command_context import CommandContext
from src.core.contracts.command_result import CommandResult


async def run(args: dict[str, str], ctx: CommandContext) -> CommandResult:
    return CommandResult.error(
        "💥 *Deliberate Error — Error-Path Test*\n"
        "──────────────────────────────────\n"
        "This error was intentional.\n"
        "If you received this reply:\n"
        "  ✅ Error was caught by Core (no crash)\n"
        "  ✅ Execution logged as failure in DB\n"
        "  ✅ send_message() still worked\n"
        "  ✅ Poll loop continues running\n"
        "──────────────────────────────────\n"
        "Error-path pipeline: *HEALTHY* ✅"
    )
