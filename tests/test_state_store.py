import pytest

from hypb.state_store import DEFAULT_DB_PATH, MASTODON, TWITTER, StateStore


@pytest.fixture
def store(tmp_path):
    return StateStore(db_path=tmp_path / "state.db")


def test_a_platform_that_has_never_posted_has_no_state(store):
    """None means 'nothing to compare against', explicitly.

    The whole point of this module: the old timeline regex returned None on no
    match too, but callers then fed it into `current > last` and crashed.
    """
    assert store.get(MASTODON) is None


def test_a_recorded_percentage_reads_back(store):
    store.set(MASTODON, 42)
    assert store.get(MASTODON) == 42


def test_recording_again_replaces_the_previous_percentage(store):
    store.set(MASTODON, 42)
    store.set(MASTODON, 43)
    assert store.get(MASTODON) == 43


def test_platforms_do_not_share_state(store):
    """The reason the table has a platform column at all.

    A run where one platform posts and the other fails must leave two different
    numbers, so the failed one retries while the successful one does not repeat.
    """
    store.set(MASTODON, 50)
    assert store.get(TWITTER) is None

    store.set(TWITTER, 49)
    assert store.get(MASTODON) == 50
    assert store.get(TWITTER) == 49


def test_state_outlives_the_process(tmp_path):
    """A container restart or host reboot must not lose the percentage."""
    db_path = tmp_path / "state.db"
    StateStore(db_path=db_path).set(MASTODON, 50)

    assert StateStore(db_path=db_path).get(MASTODON) == 50


def test_the_parent_directory_is_created(tmp_path):
    """The named volume is mounted empty; nothing else will make this path."""
    store = StateStore(db_path=tmp_path / "nested" / "dir" / "state.db")
    store.set(MASTODON, 1)

    assert (tmp_path / "nested" / "dir" / "state.db").exists()


def test_the_path_comes_from_the_environment_when_not_injected(tmp_path, monkeypatch):
    """STATE_DB_PATH is how the container points at its volume."""
    monkeypatch.setenv("STATE_DB_PATH", str(tmp_path / "from-env.db"))
    StateStore().set(MASTODON, 7)

    assert (tmp_path / "from-env.db").exists()
    assert StateStore().get(MASTODON) == 7


def test_the_default_path_is_the_documented_volume_mount():
    """deploy/progress-run.sh and docs/deployment.md both hardcode this path."""
    assert DEFAULT_DB_PATH == "/var/lib/hypb/state.db"
