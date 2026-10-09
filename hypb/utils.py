import logging
import os
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _Delivery:
    delivered: bool
    status: int | None = None


def _worth_resending_as_plain(delivery: _Delivery) -> bool:
    """A 400 means Telegram could not take the message as written.

    Usually that is markup it could not parse or a button URL it refused, which
    the plain version does not have. A wrong chat id is also a 400, so it is
    tried twice and fails both times; anything else (a wrong token is 401) would
    fail the plain version just the same and is not retried.
    """
    return not delivery.delivered and delivery.status == HTTPStatus.BAD_REQUEST


async def _post_async(session: aiohttp.ClientSession, payload: dict) -> _Delivery:
    async with session.post(TELEGRAM_API_URL, json=payload) as response:
        if not response.ok:
            logger.error("telegram rejected the alert: HTTP %s %s", response.status, redact(await response.text()))
            return _Delivery(False, response.status)
    return _Delivery(True, response.status)


async def send_async_alert(message: TelegramMessage) -> bool:
    """Send a Telegram message, reporting whether Telegram accepted it.

    The async twin of send_alert, with the same plain-text resend.
    """
    timeout = aiohttp.ClientTimeout(total=TELEGRAM_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            delivery = await _post_async(session, message.payload(CHAT_ID))
            if _worth_resending_as_plain(delivery):
                logger.warning("telegram rejected the formatted alert; resending as plain text")
                delivery = await _post_async(session, message.plain_payload(CHAT_ID))
            return delivery.delivered
    except (aiohttp.ClientError, TimeoutError) as e:
        logger.error("telegram alert could not be sent: %s", redact(repr(e)))
        return False


def _post(payload: dict) -> _Delivery:
    try:
        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=TELEGRAM_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        logger.error("telegram alert could not be sent: %s", redact(repr(e)))
        return _Delivery(False)

    if not response.ok:
        logger.error("telegram rejected the alert: HTTP %s %s", response.status_code, redact(response.text))
        return _Delivery(False, response.status_code)

    return _Delivery(True, response.status_code)


def send_alert(message: TelegramMessage) -> bool:
    """Send a Telegram message, reporting whether Telegram accepted it.

    A wrong token or chat id is not a transport error: Telegram answers 4xx
    with an `ok: false` body, which the previous fire-and-forget post discarded.
    That made a broken alerting path indistinguishable from a working one — the
    worst possible failure for the only channel this bot has to say anything is
    wrong.

    A message Telegram cannot take as written is resent once as plain text, so
    formatting is never the reason an alert is lost.
    """
    delivery = _post(message.payload(CHAT_ID))
    if _worth_resending_as_plain(delivery):
        logger.warning("telegram rejected the formatted alert; resending as plain text")
        delivery = _post(message.plain_payload(CHAT_ID))
    return delivery.delivered
