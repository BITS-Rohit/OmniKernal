"""
CommandSanitizer — Injection Prevention Layer

Standardizes and cleans raw user input before it reaches the parser.
Prevents shell injection, command chaining, newline injection, and template injection.
"""

import re


class CommandSanitizer:
    """
    Security firewall for raw message text.

    Rule: Never trust inbound text. Strip anything that isn't a
    standard character, number, or basic punctuation needed for commands.

    previously used raw string r"[...\\n\\r]" which matched the
    two-character literal sequences \\n and \\r (backslash + letter), NOT the
    actual newline (\\x0a) and carriage-return (\\x0d) control characters.
    Newline injection was therefore completely unblocked. Fixed by handling
    control characters with explicit str.replace() before the regex step.
    """

    # Shell metacharacters to strip (literal chars, not escape sequences).
    # Blocks chaining/injection tokens: ; & | ` $ \ ( ) { } < >
    # Note: ( ) are included because they appear in shell substitutions like $()
    # and serve no valid purpose in bot commands.
    FORBIDDEN_CHARS = r"[;\&|`\$\\(){}<>]"

    @classmethod
    def sanitize(cls, raw_text: str) -> str:
        """
        Cleans raw input text.

        Steps:
            1. Guard against None / falsy input
            2. Strip leading/trailing whitespace
            3. Replace actual newline/carriage-return characters with spaces
                — these were unblocked due to wrong regex previously
            4. Strip shell metacharacters via FORBIDDEN_CHARS regex
                — includes () to close the $() substitution bypass
            5. Collapse multiple spaces into one
        """
        if not raw_text:
            return ""

        text = raw_text.strip()
        text = text.replace("\n", "").replace("\r", "")
        text = re.sub(cls.FORBIDDEN_CHARS, "", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()
