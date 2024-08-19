import os

import aiohttp
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


async def send_async_alert(msg):
    async with aiohttp.ClientSession() as session, session.post(TELEGRAM_API_URL, json={"chat_id": CHAT_ID, "text": msg}) as response:
        return await response.text()


def send_alert(msg):
    response = requests.post(TELEGRAM_API_URL, json={"chat_id": CHAT_ID, "text": msg})
    return response.text
