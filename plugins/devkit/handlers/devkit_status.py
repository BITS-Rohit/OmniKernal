"""
devkit_status — Layer 5: DB Query Test

Validates: ctx._repository correctly executes multiple queries:
  - get_all_plugins() → Plugin rows
  - get_all_tools()   → Tool rows

A DB failure here (wrong session, missing table, etc.) would raise
and be caught by the dispatcher, returning a visible error instead
of a clean status reply.
"""

from src.core.contracts.command_context import CommandContext
from src.core.contracts.command_result import CommandResult


async def run(args: dict[str, str], ctx: CommandContext) -> CommandResult:
    repo = ctx._repository
    if repo is None:
        return CommandResult.error("Handler context is missing repository reference.")

    plugins = await repo.get_all_plugins()
    tools = await repo.get_all_tools()

    active_plugins = [p for p in plugins if p.is_active]
    inactive_plugins = [p for p in plugins if not p.is_active]

    plugin_lines = []
    for p in plugins:
        icon = "✅" if p.is_active else "❌"
        plugin_lines.append(f"  {icon} {p.name} v{p.version}")

    tool_lines = [f"  🔧 !{t.command_name}" for t in tools]

    return CommandResult.success(
        reply=(
            f"📊 *OmniKernal DevKit — System Status*\n"
            f"══════════════════════════════\n"
            f"🧩 *Plugins* ({len(active_plugins)} active / {len(inactive_plugins)} inactive)\n"
            + "\n".join(plugin_lines) + "\n"
            f"──────────────────────────────\n"
            f"⚙️ *Registered Commands* ({len(tools)} total)\n"
            + "\n".join(tool_lines) + "\n"
            f"══════════════════════════════\n"
            f"✅ DB repo queries healthy."
        )
    )
