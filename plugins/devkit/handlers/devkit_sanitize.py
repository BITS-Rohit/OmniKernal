"""
devkit_sanitize — Layer 3: Sanitizer Visibility Test

Validates: The CommandSanitizer correctly strips shell metacharacters,
injection tokens, newlines, and collapses whitespace.

Edge cases you can test by sending:
  !devkit_sanitize hello; rm -rf /        → strips ;
  !devkit_sanitize $(whoami)              → strips $ (
  !devkit_sanitize hello && cat /etc/passwd → strips &&
  !devkit_sanitize `id`                   → strips backtick
  !devkit_sanitize hello | cat            → strips |
  !devkit_sanitize hello\\ninjected       → strips backslash

IMPORTANT: The payload this handler receives has ALREADY been sanitized
by the Core. So this handler shows the post-sanitized text, revealing
exactly what the sanitizer allowed through vs. stripped.
"""

from src.core.contracts.command_context import CommandContext
from src.core.contracts.command_result import CommandResult
from src.security.sanitizer import CommandSanitizer

# Shell injection tokens that should never survive sanitization
_DANGEROUS_TOKENS = [";", "&&", "||", "|", "`", "$(", "${", "\\n", "\\r"]


async def run(args: dict[str, str], ctx: CommandContext) -> CommandResult:
    received = args.get("payload", "")

    # Double-sanitize to show idempotency (sanitizing again should not change output)
    double_sanitized = CommandSanitizer.sanitize(received)
    is_idempotent = (received == double_sanitized)

    # Check if any dangerous tokens survived (they shouldn't)
    survivors = [tok for tok in _DANGEROUS_TOKENS if tok in received]

    if survivors:
        danger_note = f"⚠️ Escaped tokens survived: {survivors}\n*Review sanitizer — possible bypass!*"
    else:
        danger_note = "✅ All injection tokens stripped by sanitizer."

    return CommandResult.success(
        reply=(
            f"🔬 *Sanitizer Edge Case Test*\n"
            f"─────────────────────────\n"
            f"📥 Received (post-sanitize):\n`{received}`\n"
            f"─────────────────────────\n"
            f"🔁 Idempotent: {'Yes ✅' if is_idempotent else 'No ⚠️'}\n"
            f"{danger_note}"
        )
    )
