"""
Handler for: !sys plugins

Lists all plugins currently registered in the OmniKernal DB registry.
Used as an end-to-end smoke test — verifies the full pipeline:
  WhatsApp message → Core → Router → Dispatcher → Handler → DB → Reply

Design note: handlers MUST NOT open their own DB sessions.
The CommandContext carries a reference to the per-request repository
(ctx._repository). This is the only sanctioned DB access point in handlers.
"""

from src.core.contracts.command_context import CommandContext
from src.core.contracts.command_result import CommandResult


async def run(args: dict[str, str], ctx: CommandContext) -> CommandResult:
    """
    Handler for "!sys plugins"
    Returns a list of all plugins from the DB registry to test end-to-end connectivity.
    """
    # Use the per-request repository injected by the Core — never open a raw session.
    repo = ctx._repository
    if repo is None:
        return CommandResult.error("Handler context is missing repository reference.")

    plugins = await repo.get_all_plugins()

    if not plugins:
        return CommandResult.success(reply="No plugins are currently registered in the system.")

    lines = ["⚙️ *OmniKernal Plugin Registry*"]
    for p in plugins:
        status = "✅" if p.is_active else "❌"
        lines.append(f"{status} {p.name} v{p.version}")

    return CommandResult.success(reply="\n".join(lines))
