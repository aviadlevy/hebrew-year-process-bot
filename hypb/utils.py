import logging
import os

import aiohttp
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

TELEGRAM_TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)


def redact(text: str) -> str:
    """Strip the bot token out of text destined for the log.

    The token is part of the API URL, so requests puts it verbatim into the
    message of any transport error ("Max retries exceeded with url:
    /bot<TOKEN>/sendMessage"). Logging such an exception raw would publish the
    token to the container logs.
    """
    if TELEGRAM_TOKEN:
        return text.replace(TELEGRAM_TOKEN, "***")
    return text


async def send_async_alert(msg):
    async with aiohttp.ClientSession() as session, session.post(TELEGRAM_API_URL, json={"chat_id": CHAT_ID, "text": msg}) as response:
        return await response.text()


def send_alert(msg) -> bool:
    """Send a Telegram message, reporting whether Telegram accepted it.

    A wrong token or chat id is not a transport error: Telegram answers 4xx
    with an `ok: false` body, which the previous fire-and-forget post discarded.
    That made a broken alerting path indistinguishable from a working one — the
    worst possible failure for the only channel this bot has to say anything is
    wrong.
    """
    try:
        response = requests.post(
            TELEGRAM_API_URL,
            json={"chat_id": CHAT_ID, "text": msg},
            timeout=TELEGRAM_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        logger.error("telegram alert could not be sent: %s", redact(repr(e)))
        return False

    if not response.ok:
        logger.error("telegram rejected the alert: HTTP %s %s", response.status_code, redact(response.text))
        return False

    return True
