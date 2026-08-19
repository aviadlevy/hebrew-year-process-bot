from unittest.mock import MagicMock, patch

import pytest

from hypb.settings import REQUIRED_PROGRESS_VARS
from hypb.state_store import MASTODON, TWITTER, StateStore
from hypb.tweet_progress import account_statuses, get_progress_bar, main, toot, tweet

FIFTY_PRECENT_BAR = "▓▓▓▓▓▓▓▓░░░░░░░ 50%"


@pytest.mark.asyncio
async def test_toot(mocker):
    mastodon_client = MagicMock()
    mastodon_client.toot.return_value = "Toot successful"

    with patch("hypb.tweet_progress.run_in_executor", return_value=toot):
        result = await toot(mastodon_client, "Test Toot")
        assert result == "Toot successful"


@pytest.mark.asyncio
async def test_account_statuses(mocker):
    mastodon_client = MagicMock()
    mastodon_client.account_statuses.return_value = ["Toot 1", "Toot 2"]

    with patch("hypb.tweet_progress.run_in_executor", return_value=account_statuses):
        result = await account_statuses(mastodon_client)
        assert result == ["Toot 1", "Toot 2"]


def test_get_progress_bar():
    current_state = 50  # Adjust the current state as needed
    progress_bar = get_progress_bar(current_state)
    expected_progress_bar = FIFTY_PRECENT_BAR
    assert progress_bar == expected_progress_bar


FORTY_NINE_PERCENT_TOOT = {"content": "<p>▓▓▓▓▓▓▓░░░░░░░░ 49%</p>"}


@pytest.fixture
def store(tmp_path, mocker):
    """A real store on a temp file, so the tests exercise the actual SQL."""
    real = StateStore(db_path=tmp_path / "state.db")
    mocker.patch("hypb.tweet_progress.StateStore", return_value=real)
    return real


@pytest.fixture
def clients(mocker):
    """Both platform clients, patched in and handed back for assertions."""
    mastodon_client = MagicMock()
    twitter_client = MagicMock()
    twitter_client.create_tweet = mocker.AsyncMock(return_value="Tweet successful")
    mastodon_client.toot.return_value = "Toot"
    mastodon_client.account_statuses.return_value = [FORTY_NINE_PERCENT_TOOT]

    mocker.patch("hypb.tweet_progress.get_mastodon_client", return_value=mastodon_client)
    mocker.patch("hypb.tweet_progress.get_async_twitter_client", return_value=twitter_client)
    mocker.patch("hypb.tweet_progress.get_current_state", return_value=50)
    mocker.patch("hypb.tweet_progress.send_async_alert", new=mocker.AsyncMock())
    return mastodon_client, twitter_client


@pytest.mark.asyncio
async def test_an_empty_store_seeds_from_the_timeline_and_posts(store, clients):
    """First run on the host: the timeline is the only history that exists."""
    mastodon_client, twitter_client = clients

    assert await tweet() == 0

    twitter_client.create_tweet.assert_called_with(text=FIFTY_PRECENT_BAR)
    mastodon_client.toot.assert_called_with(FIFTY_PRECENT_BAR)
    assert store.get(MASTODON) == 50
    assert store.get(TWITTER) == 50


@pytest.mark.asyncio
async def test_a_seed_fetch_failure_aborts_without_writing_any_state(store, clients):
    """A transient Mastodon outage during seeding must not be mistaken for an empty window.

    An empty window is D3's conservative case: record without posting, exit 0.
    A fetch failure is different -- we never actually learned whether a
    progress toot exists -- so the run must abort with no row written at all,
    leaving the next run free to retry the seed cleanly.
    """
    mastodon_client, twitter_client = clients
    mastodon_client.account_statuses.side_effect = RuntimeError("mastodon is down")

    assert await tweet() == 1

    assert not twitter_client.create_tweet.called
    assert not mastodon_client.toot.called
    assert store.get(MASTODON) is None
    assert store.get(TWITTER) is None


@pytest.mark.asyncio
async def test_nothing_is_posted_when_there_is_no_history_to_seed_from(store, clients):
    """The TypeError case, end to end.

    Fifty statuses with no progress bar used to mean `current > None` and a raw
    traceback. Recording without posting costs at most one skipped day; posting
    could duplicate a percentage that already went out.
    """
    mastodon_client, twitter_client = clients
    mastodon_client.account_statuses.return_value = [{"content": "<p>Something else on my mind</p>"}]

    assert await tweet() == 0

    assert not twitter_client.create_tweet.called
    assert not mastodon_client.toot.called
    assert store.get(MASTODON) == 50
    assert store.get(TWITTER) == 50


@pytest.mark.asyncio
async def test_the_stored_percentage_wins_over_the_timeline(store, clients):
    """Once written, the database is authoritative and Mastodon is not read."""
    mastodon_client, twitter_client = clients
    store.set(MASTODON, 50)
    store.set(TWITTER, 50)

    assert await tweet() == 0

    assert not mastodon_client.account_statuses.called
    assert not twitter_client.create_tweet.called
    assert not mastodon_client.toot.called


@pytest.mark.asyncio
async def test_a_twitter_failure_still_toots_and_is_reported(store, clients):
    """The reason state is per platform.

    Twitter used to be awaited first, so its failure meant Mastodon never got
    the toot -- and the run died before saying which half broke.
    """
    mastodon_client, twitter_client = clients
    twitter_client.create_tweet.side_effect = RuntimeError("403 Forbidden")
    store.set(MASTODON, 49)
    store.set(TWITTER, 49)

    assert await tweet() == 1

    mastodon_client.toot.assert_called_with(FIFTY_PRECENT_BAR)
    assert store.get(MASTODON) == 50
    assert store.get(TWITTER) == 49, "a failed post must not advance its platform"


@pytest.mark.asyncio
async def test_a_mastodon_failure_still_tweets_and_is_reported(store, clients):
    """The symmetric case: a Mastodon-side failure must not block Twitter either.

    D1 is per-platform in both directions, not just the one this branch was
    written to fix.
    """
    mastodon_client, twitter_client = clients
    mastodon_client.toot.side_effect = RuntimeError("mastodon.social is down")
    store.set(MASTODON, 49)
    store.set(TWITTER, 49)

    assert await tweet() == 1

    twitter_client.create_tweet.assert_called_with(text=FIFTY_PRECENT_BAR)
    assert store.get(TWITTER) == 50
    assert store.get(MASTODON) == 49, "a failed post must not advance its platform"


@pytest.mark.asyncio
async def test_a_failed_platform_retries_on_the_next_run(store, clients):
    """Because the row did not advance, the next run tries Twitter again."""
    mastodon_client, twitter_client = clients
    store.set(MASTODON, 50)
    store.set(TWITTER, 49)

    assert await tweet() == 0

    twitter_client.create_tweet.assert_called_with(text=FIFTY_PRECENT_BAR)
    assert not mastodon_client.toot.called, "mastodon is already current and must not repeat itself"
    assert store.get(TWITTER) == 50


@pytest.mark.asyncio
async def test_the_year_rolling_over_posts_zero_percent(store, clients, mocker):
    """last=100, current=0 is the one case where current < last and we still post."""
    mastodon_client, twitter_client = clients
    mocker.patch("hypb.tweet_progress.get_current_state", return_value=0)
    store.set(MASTODON, 100)
    store.set(TWITTER, 100)

    assert await tweet() == 0

    assert mastodon_client.toot.called
    assert twitter_client.create_tweet.called
    assert store.get(MASTODON) == 0


def test_main_returns_2_on_missing_config(monkeypatch):
    """main() must fail fast on missing config, before ever reaching asyncio.run(tweet())."""
    for var in REQUIRED_PROGRESS_VARS:
        monkeypatch.delenv(var, raising=False)

    assert main() == 2


def test_main_returns_1_and_alerts_when_tweet_raises(monkeypatch, mocker):
    """A crash before the summary must still page, not just leave a traceback in journald.

    StateStore() failing to open its database file, or any other exception
    raised before tweet() reaches its own alert, used to escape asyncio.run as
    a bare traceback with nothing sent to Telegram -- the job's only
    observability. main() must catch it, log it, alert, and return 1.
    """
    for var in REQUIRED_PROGRESS_VARS:
        monkeypatch.setenv(var, "test-value")

    mocker.patch("hypb.tweet_progress.tweet", side_effect=RuntimeError("unable to open database file"))
    send_async_alert = mocker.patch("hypb.tweet_progress.send_async_alert", new=mocker.AsyncMock())

    assert main() == 1
    assert send_async_alert.called
