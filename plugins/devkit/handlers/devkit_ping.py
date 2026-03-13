"""
devkit_ping — Layer 1: Basic Routing Test

Validates: Router lookup → handler lazy-load → CommandResult → send_message.
If this works, the entire core dispatch chain is healthy.
Expected reply: 🏓 PONG with timestamp.
"""

from datetime import datetime, timezone

from src.core.contracts.command_context import CommandContext
from src.core.contracts.command_result import CommandResult


async def run(args: dict[str, str], ctx: CommandContext) -> CommandResult:
    now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    return CommandResult.success(
        reply=(
            "🏓 *PONG!*\n"
            f"⚡ OmniKernal DevKit is alive.\n"
            f"🕐 Core time: `{now}`\n"
            f"✅ Pipeline: Adapter → Sanitizer → Router → DB → Handler → Reply"
        )
    )
