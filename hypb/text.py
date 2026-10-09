"""Shortening text from outside, so one long toot or traceback cannot bury the rest."""


def utf16_len(text: str) -> int:
    """Length as Telegram counts it: UTF-16 code units, so an emoji outside the BMP is two."""
    return len(text.encode("utf-16-le")) // 2


def truncate(text: str, limit: int) -> str:
    """Keep the start; say how much was dropped."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [{len(text) - limit} more chars]"


def _trimmed_notice(dropped: int) -> str:
    return f"… {dropped} earlier characters trimmed\n"


def keep_end(text: str, limit: int) -> str:
    """Keep the end within `limit` UTF-16 units, notice included.

    For tracebacks, whose last lines name the failure, and for anything that
    must fit Telegram's limit. Characters are taken whole from the end, so a
    surrogate pair is never split.
    """
    if utf16_len(text) <= limit:
        return text
    # The notice is sized for the most it could ever report, so the tail chosen
    # against it can only leave room to spare.
    room = limit - utf16_len(_trimmed_notice(len(text)))
    kept = 0
    used = 0
    for char in reversed(text):
        width = utf16_len(char)
        if used + width > room:
            break
        used += width
        kept += 1
    tail = text[len(text) - kept :] if kept else ""
    return _trimmed_notice(len(text) - kept) + tail
