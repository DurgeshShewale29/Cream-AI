"""Security guardrails, input validation, and prompt-injection detection for ScholarSetu."""

from __future__ import annotations

import re

MAX_QUESTION_LENGTH = 500
MAX_QUERY_LENGTH = 200

# Adversarial prompt-injection, jailbreak, and system override patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"you\s+are\s+now\s+(an?\s+unrestricted|dan|jailbreak)",
    r"system\s+override",
    r"reveal\s+(the\s+|your\s+)?(system\s+prompt|prompt|instructions)",
    r"print\s+(the\s+|your\s+)?(system\s+prompt|instructions)",
    r"say\s+['\"]?pwned['\"]?",
    r"output\s+['\"]?pwned['\"]?",
    r"bypass\s+all\s+(rules|restrictions|guardrails)",
    r"act\s+as\s+(an?\s+evil|unrestricted|mode)",
]

_INJECTION_REGEX = re.compile(
    "|".join(f"({p})" for p in INJECTION_PATTERNS),
    re.IGNORECASE,
)


def is_prompt_injection(text: str) -> bool:
    """Return True if the input matches known adversarial prompt injection patterns."""
    if not text:
        return False
    return bool(_INJECTION_REGEX.search(text))


def validate_input(text: str, max_length: int = MAX_QUESTION_LENGTH) -> tuple[bool, str]:
    """Validate input boundaries and sanitize against null bytes and control chars.

    Returns (is_valid, sanitized_or_error_message).
    """
    if not text or not text.strip():
        return False, "Input cannot be empty or only whitespace."
    stripped = text.strip()
    if len(stripped) > max_length:
        return False, f"Input length ({len(stripped)}) exceeds maximum allowed ({max_length} characters)."
    if "\x00" in stripped:
        return False, "Input contains illegal null bytes."
    return True, stripped
