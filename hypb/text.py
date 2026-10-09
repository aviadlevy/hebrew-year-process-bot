"""Shortening text from outside, so one long toot or traceback cannot bury the rest."""


def utf16_len(text: str) -> int:
    """Length as Telegram counts it: UTF-16 code units, so an emoji outside the BMP is two."""
    return len(text.encode("utf-16-le")) // 2


#: The last codepoint UTF-16 encodes in one unit; anything above takes a surrogate pair.
_LAST_BMP_CODEPOINT = 0xFFFF


def _units(char: str) -> int:
    """UTF-16 width of one character, without encoding it: two above the BMP."""
    return 2 if ord(char) > _LAST_BMP_CODEPOINT else 1


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
    # against it can only leave room to spare. When even the notice does not
    # fit, the tail goes alone: the limit is never exceeded.
    notice_units = utf16_len(_trimmed_notice(len(text)))
    with_notice = limit > notice_units
    tail = _tail_within(text, limit - notice_units if with_notice else limit)
    return _trimmed_notice(len(text) - len(tail)) + tail if with_notice else tail


def _tail_within(text: str, room: int) -> str:
    kept = 0
    used = 0
    for char in reversed(text):
        used += _units(char)
        if used > room:
            break
        kept += 1
    return text[len(text) - kept :] if kept else ""
