"""Alerts: a title you can read at a glance, the error, and the traceback folded away.

The traceback is what a human needs to debug, but it is noise in a chat, so it
goes in a collapsed quote. It is also the only part that can grow without
bound, so it is the part that gets trimmed to keep the alert under Telegram's
limit -- from the front, because the end of a traceback is where the failure is.
"""

import traceback

from hypb.telegram_message import TelegramMessage, bold, code, expandable_quote
from hypb.text import keep_end, truncate

#: Room left for the title and the error line out of Telegram's 4096.
MAX_TRACEBACK_CHARS = 3000

MAX_ERROR_CHARS = 500


def format_traceback(error: BaseException) -> str:
    return "".join(traceback.format_exception(error)).rstrip()


def error_alert(title: str, error: BaseException) -> TelegramMessage:
    return TelegramMessage(
        "\n".join(
            [
                f"🚨 {bold(title)}",
                code(truncate(repr(error), MAX_ERROR_CHARS)),
                expandable_quote(keep_end(format_traceback(error), MAX_TRACEBACK_CHARS)),
            ]
        )
    )


def warning_alert(title: str, detail: str) -> TelegramMessage:
    return TelegramMessage(f"⚠️ {bold(title)}\n{code(truncate(detail, MAX_ERROR_CHARS))}")

