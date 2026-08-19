"""Transport behaviour of the async Telegram alert.

The progress job is a one-shot whose logs nobody watches, so Telegram is its
only observability. An alert that fails silently is indistinguishable from a
run with nothing to report -- the worst possible failure for the only channel
this bot has to say anything is wrong. `send_alert` was hardened for the
replier in #82; this is the same contract for the async path.
"""

import logging

import aiohttp
import pytest

from hypb.utils import send_async_alert


class _FakeResponse:
    def __init__(self, ok, status=200, text="ok"):
        self.ok = ok
        self.status = status
        self._text = text

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    def post(self, *args, **kwargs):
        if self._error is not None:
            raise self._error
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.mark.asyncio
async def test_a_delivered_alert_is_confirmed(mocker):
    mocker.patch("hypb.utils.aiohttp.ClientSession", return_value=_FakeSession(response=_FakeResponse(ok=True)))

    assert await send_async_alert("hello") is True


@pytest.mark.asyncio
async def test_a_rejected_alert_is_reported_instead_of_swallowed(mocker, caplog):
    """A bad chat id is HTTP 400 with ok:false -- not an exception.

    The old code returned response.text() and no caller looked at it.
    """
    response = _FakeResponse(ok=False, status=400, text='{"ok":false,"description":"chat not found"}')
    mocker.patch("hypb.utils.aiohttp.ClientSession", return_value=_FakeSession(response=response))

    with caplog.at_level(logging.ERROR):
        assert await send_async_alert("hello") is False

    assert "chat not found" in caplog.text


@pytest.mark.asyncio
async def test_an_undeliverable_alert_is_reported_without_raising(mocker, caplog):
    """A failed alert must not become the exception that ends the run."""
    error = aiohttp.ClientConnectionError("connection refused")
    mocker.patch("hypb.utils.aiohttp.ClientSession", return_value=_FakeSession(error=error))

    with caplog.at_level(logging.ERROR):
        assert await send_async_alert("hello") is False

    assert "could not be sent" in caplog.text


@pytest.mark.asyncio
async def test_the_bot_token_never_reaches_the_log(mocker, caplog, monkeypatch):
    """The token is in the URL, so requests' error text carries it verbatim."""
    monkeypatch.setattr("hypb.utils.TELEGRAM_TOKEN", "123456:secret-token")
    error = aiohttp.ClientConnectionError("Cannot connect to /bot123456:secret-token/sendMessage")
    mocker.patch("hypb.utils.aiohttp.ClientSession", return_value=_FakeSession(error=error))

    with caplog.at_level(logging.ERROR):
        await send_async_alert("hello")

    assert "secret-token" not in caplog.text
    assert "***" in caplog.text


@pytest.mark.asyncio
async def test_a_bare_timeout_is_reported_without_raising(mocker, caplog):
    """asyncio.TimeoutError is the builtin TimeoutError on Python 3.11+, and it is
    NOT an aiohttp.ClientError subclass -- it needs its own entry in the except
    tuple. If that tuple is ever "simplified" to aiohttp.ClientError alone, a real
    timeout would propagate and crash the caller instead of being reported here.
    """
    error = TimeoutError("timed out")
    mocker.patch("hypb.utils.aiohttp.ClientSession", return_value=_FakeSession(error=error))

    with caplog.at_level(logging.ERROR):
        assert await send_async_alert("hello") is False

    assert "could not be sent" in caplog.text


@pytest.mark.asyncio
async def test_a_rejected_alert_also_redacts_the_token(mocker, caplog, monkeypatch):
    """redact() is applied on both the exception path and the rejection path.

    Only the exception path had a redaction test; a regression that dropped
    redact() from the rejection branch would go unnoticed otherwise.
    """
    monkeypatch.setattr("hypb.utils.TELEGRAM_TOKEN", "123456:secret-token")
    response = _FakeResponse(ok=False, status=400, text="chat not found for bot123456:secret-token")
    mocker.patch("hypb.utils.aiohttp.ClientSession", return_value=_FakeSession(response=response))

    with caplog.at_level(logging.ERROR):
        assert await send_async_alert("hello") is False

    assert "secret-token" not in caplog.text
    assert "***" in caplog.text
