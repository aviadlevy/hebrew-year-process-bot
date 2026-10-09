import logging
import os
from http import HTTPStatus

import aiohttp
import requests

from hypb.telegram_message import TelegramMessage

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


async def _post_async(session: aiohttp.ClientSession, payload: dict) -> tuple[bool, int | None]:
    async with session.post(TELEGRAM_API_URL, json=payload) as response:
        if not response.ok:
            logger.error("telegram rejected the alert: HTTP %s %s", response.status, redact(await response.text()))
            return False, response.status
    return True, response.status


async def send_async_alert(message: TelegramMessage) -> bool:
    """Send a Telegram message, reporting whether Telegram accepted it.

    The async twin of send_alert, and hardened for the same reason: a wrong
    token or chat id is answered with 4xx and `ok: false` rather than a
    transport error, so the previous fire-and-forget post could not tell a
    working alerting path from a broken one.
    """
    timeout = aiohttp.ClientTimeout(total=TELEGRAM_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            delivered, status = await _post_async(session, message.payload(CHAT_ID))
            if delivered or status != HTTPStatus.BAD_REQUEST:
                return delivered
            logger.warning("telegram rejected the formatted alert; resending as plain text")
            delivered, _ = await _post_async(session, message.plain_payload(CHAT_ID))
            return delivered
    except (aiohttp.ClientError, TimeoutError) as e:
        logger.error("telegram alert could not be sent: %s", redact(repr(e)))
        return False


def _post(payload: dict) -> tuple[bool, int | None]:
    try:
        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=TELEGRAM_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        logger.error("telegram alert could not be sent: %s", redact(repr(e)))
        return False, None

    if not response.ok:
        logger.error("telegram rejected the alert: HTTP %s %s", response.status_code, redact(response.text))
        return False, response.status_code

    return True, response.status_code


def send_alert(message: TelegramMessage) -> bool:
    """Send a Telegram message, reporting whether Telegram accepted it.

    A wrong token or chat id is not a transport error: Telegram answers 4xx
    with an `ok: false` body, which the previous fire-and-forget post discarded.
    That made a broken alerting path indistinguishable from a working one — the
    worst possible failure for the only channel this bot has to say anything is
    wrong.

    A 400 means Telegram could not take the message as written -- markup it
    could not parse, or text over its limit -- so the message is resent once as
    plain text. Formatting must never be the reason an alert is lost. Any other
    rejection (a wrong token or chat id) would fail the plain version too.
    """
    delivered, status = _post(message.payload(CHAT_ID))
    if delivered or status != HTTPStatus.BAD_REQUEST:
        return delivered
    logger.warning("telegram rejected the formatted alert; resending as plain text")
    delivered, _ = _post(message.plain_payload(CHAT_ID))
    return delivered
