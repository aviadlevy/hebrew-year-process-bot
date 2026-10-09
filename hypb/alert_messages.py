"""Alerts: a title you can read at a glance, the error, and the traceback folded away.

The traceback is what a human needs to debug, but it is noise in a chat, so it
travels as the message's collapsed details, which give way first when the
message would not fit.
"""

import traceback

from hypb.telegram_message import TelegramMessage, bold, code
from hypb.text import truncate

#: The error line is a headline; the full text is at the end of the traceback anyway.
MAX_ERROR_CHARS = 150


def format_traceback(error: BaseException) -> str:
    return "".join(traceback.format_exception(error)).rstrip()


def error_line(error: BaseException) -> str:
    """The exception as one short monospace line, shared by alerts and failed-mention cards."""
    return code(truncate(repr(error), MAX_ERROR_CHARS))


def error_alert(title: str, error: BaseException) -> TelegramMessage:
    return TelegramMessage(f"🚨 {bold(title)}\n{error_line(error)}", details=format_traceback(error))


def warning_alert(title: str, error: BaseException) -> TelegramMessage:
    """Like an error alert, for something still being retried."""
    return TelegramMessage(f"⚠️ {bold(title)}\n{error_line(error)}", details=format_traceback(error))
