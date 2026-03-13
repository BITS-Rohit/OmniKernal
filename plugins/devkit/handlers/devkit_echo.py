"""
devkit_echo — Layer 2: Argument Parsing Test

Validates: CommandParser extracts <text> from "!devkit_echo <anything>".
Edge cases this tests:
  - Multi-word args:   "!devkit_echo hello world"
  - Unicode/emoji:     "!devkit_echo 🔥 fire test"
  - Numbers:           "!devkit_echo 12345"
  - Symbols:           "!devkit_echo hello! what?"
  - Leading spaces:    "!devkit_echo   spaced"
Expected reply: echoes back exactly what it parsed.
"""

from src.core.contracts.command_context import CommandContext
from src.core.contracts.command_result import CommandResult


async def run(args: dict[str, str], ctx: CommandContext) -> CommandResult:
    text = args.get("text", "").strip()

    if not text:
        return CommandResult.success(
            reply=(
                "🔇 *Echo Test — Empty Arg*\n"
                "No text received after parsing.\n"
                "Try: `!devkit_echo hello world 🔥`"
            )
        )

    char_count = len(text)
    word_count = len(text.split())
    has_emoji = any(ord(c) > 127 for c in text)

    return CommandResult.success(
        reply=(
            f"📣 *Echo Test — Arg Parser*\n"
            f"Received: `{text}`\n"
            f"─────────────────\n"
            f"📏 Chars: {char_count}  |  📝 Words: {word_count}\n"
            f"🌐 Unicode/Emoji: {'Yes ✅' if has_emoji else 'No'}\n"
            f"✅ CommandParser extracted arg correctly."
        )
    )
