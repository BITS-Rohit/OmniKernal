"""
devkit_whoami — Layer 4: User Context Injection Test

Validates: ctx.user is correctly populated with:
  - user.id        → sender identity from the adapter
  - user.platform  → "whatsapp" (set by the adapter)
  - ctx._tool_id   → integer PK from DB row for this command

If user.id shows "Tweakio" (or your contact name) and platform shows
"whatsapp", the full adapter → Core → ctx injection chain is verified.
"""

from src.core.contracts.command_context import CommandContext
from src.core.contracts.command_result import CommandResult


async def run(args: dict[str, str], ctx: CommandContext) -> CommandResult:
    user = ctx.user
    tool_id = ctx._tool_id

    return CommandResult.success(
        reply=(
            f"👤 *Who Am I? — Context Injection Test*\n"
            f"─────────────────────────────────\n"
            f"🆔 User ID:      `{user.id}`\n"
            f"📛 Display Name: `{user.display_name}`\n"
            f"📡 Platform:     `{user.platform}`\n"
            f"🔧 Tool ID (DB): `{tool_id}`\n"
            f"─────────────────────────────────\n"
            f"✅ CommandContext injected correctly by Core."
        )
    )
