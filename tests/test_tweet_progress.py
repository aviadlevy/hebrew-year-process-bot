from unittest.mock import MagicMock, patch

import pytest

from src.tweet_progress import get_progress_bar, timeline_home, toot, tweet

FIFTY_PRECENT_BAR = "▓▓▓▓▓▓▓▓░░░░░░░ 50%"


@pytest.mark.asyncio
async def test_toot(mocker):
    mastodon_client = MagicMock()
    mastodon_client.toot.return_value = "Toot successful"

    with patch("tweet_progress.run_in_executor", return_value=toot):
        result = await toot(mastodon_client, "Test Toot")
        assert result == "Toot successful"


@pytest.mark.asyncio
async def test_timeline_home(mocker):
    mastodon_client = MagicMock()
    mastodon_client.timeline_home.return_value = ["Toot 1", "Toot 2"]

    with patch("tweet_progress.run_in_executor", return_value=timeline_home):
        result = await timeline_home(mastodon_client)
        assert result == ["Toot 1", "Toot 2"]


def test_get_progress_bar():
    current_state = 50  # Adjust the current state as needed
    progress_bar = get_progress_bar(current_state)
    expected_progress_bar = FIFTY_PRECENT_BAR
    assert progress_bar == expected_progress_bar


# You can write more comprehensive tests for the 'should_tweet' and 'get_last_state' functions if necessary

# Mocking async functions in 'tweet' for testing
@pytest.mark.asyncio
async def test_tweet(mocker):
    mocker.patch("src.tweet_progress.get_current_state", return_value=50)  # Adjust the current state as needed

    mock_twitter_client = MagicMock()
    mock_mastodon_client = MagicMock()

    async def mock_create_tweet(**kwargs):
        return "Tweet successful"

    mocker.patch("src.tweet_progress.get_async_twitter_client", return_value=mock_twitter_client)
    mocker.patch("src.tweet_progress.get_mastodon_client", return_value=mock_mastodon_client)
    mock_mastodon_client.timeline_home.return_value = [{"content": "<p>▓▓▓▓▓▓▓▓░░░░░░░ 49%</p>"},
                                                       {"content": "<p>▓▓▓▓▓▓▓▓░░░░░░░ 48%</p>"}]
    mock_twitter_client.create_tweet.return_value = mock_create_tweet()
    mock_mastodon_client.toot.return_value = "Toot"
    mocker.patch("src.tweet_progress.send_async_alert", return_value=None)

    result = await tweet()
    assert result == 0
    mock_twitter_client.create_tweet.assert_called_with(text=FIFTY_PRECENT_BAR)
    mock_mastodon_client.toot.assert_called_with(FIFTY_PRECENT_BAR)
