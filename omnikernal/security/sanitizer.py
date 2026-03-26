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

    BUG 17 fix: previously used raw string r"[...\\n\\r]" which matched the
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
             — BUG 17 fix: these were unblocked due to wrong regex previously
          4. Strip shell metacharacters via FORBIDDEN_CHARS regex
             — includes () to close the $() substitution bypass (BUG 78 revert)
          5. Collapse multiple spaces into one
        """
        if not raw_text:
            return ""

        # 1. Basic trim
        text = raw_text.strip()

        # 2. Strip actual newline / carriage-return control chars.
        #    Delete them (don't replace with space) so newline injection
        #    cannot be used to sneak extra tokens past the parser.
        text = text.replace("\n", "").replace("\r", "")

        # 3. Strip shell metacharacters (including parens that enable $() vectors)
        text = re.sub(cls.FORBIDDEN_CHARS, "", text)

        # 4. Collapse multiple spaces into one
        text = re.sub(r"\s+", " ", text)

        return text.strip()
