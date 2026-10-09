"""Shortening text from outside, so one long toot or traceback cannot bury the rest."""


def truncate(text: str, limit: int) -> str:
    """Keep the start; say how much was dropped."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [{len(text) - limit} more chars]"


def keep_end(text: str, limit: int) -> str:
    """Keep the end; for tracebacks, whose last lines name the failure."""
    if len(text) <= limit:
        return text
    return f"… {len(text) - limit} earlier characters trimmed\n" + text[-limit:]
