import pytest

from hypb.settings import ConfigurationError, missing_variables, require

REQUIRED = ("MASTODON_ACCESS_TOKEN", "MASTODON_BASE_URL")
COMPLETE = {"MASTODON_ACCESS_TOKEN": "token", "MASTODON_BASE_URL": "https://mastodon.social"}


def test_no_missing_variables_when_all_present():
    assert missing_variables(REQUIRED, COMPLETE) == []


@pytest.mark.parametrize("absent", REQUIRED)
def test_reports_an_absent_variable(absent):
    env = {k: v for k, v in COMPLETE.items() if k != absent}
    assert missing_variables(REQUIRED, env) == [absent]


@pytest.mark.parametrize("blank", REQUIRED)
def test_reports_an_empty_variable(blank):
    """An empty token is as broken as an absent one and fails just as silently."""
    env = COMPLETE | {blank: ""}
    assert missing_variables(REQUIRED, env) == [blank]


def test_whitespace_only_counts_as_empty():
    env = COMPLETE | {"MASTODON_ACCESS_TOKEN": "   "}
    assert missing_variables(REQUIRED, env) == ["MASTODON_ACCESS_TOKEN"]


def test_reports_every_missing_variable_not_just_the_first():
    assert missing_variables(REQUIRED, {}) == list(REQUIRED)


def test_require_passes_when_complete():
    require(REQUIRED, COMPLETE)


def test_require_raises_naming_the_missing_variables():
    with pytest.raises(ConfigurationError) as excinfo:
        require(REQUIRED, {})
    message = str(excinfo.value)
    assert "MASTODON_ACCESS_TOKEN" in message
    assert "MASTODON_BASE_URL" in message
