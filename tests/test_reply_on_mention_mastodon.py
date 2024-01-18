import random

from mastodon import Mastodon

from hypb.dates_helper import get_current_date, get_current_parashah
from hypb.stream_listener_mastodon import _StreamingListener


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def create_notification(message, status_id):
    return dotdict({
        "id": random.randint(0, 100),
        "type": "mention",
        "status": dotdict({
            "content": message,
            "id": status_id
        })
    })


class TestMastodon(Mastodon):
    def __init__(self):
        super().__init__(api_base_url="testApi")


def base_flow(mocker, message):
    mastodon: Mastodon = TestMastodon()
    mocker.patch.object(mastodon, "status_reply")
    spy = mocker.spy(mastodon, "status_reply")
    stream_client = _StreamingListener(mastodon)
    status_id = random.randint(0, 100)
    notification = create_notification(message, status_id)
    stream_client.on_notification(notification)
    return spy, notification["status"]


def test_date(mocker):
    spy, notification_status = base_flow(mocker, "What's the date?")
    spy.assert_called_once_with(to_status=notification_status, status=f"The date is:\n{get_current_date(lang='eng')}")


def test_date_heb(mocker):
    spy, notification_status = base_flow(mocker, "מה התאריך?")
    spy.assert_called_once_with(to_status=notification_status, status=f"התאריך הוא:\n{get_current_date(lang='heb')}")


def test_parashah(mocker):
    spy, notification_status = base_flow(mocker, "What's the parashah?")
    spy.assert_called_once_with(to_status=notification_status,
                                status=f"The Parashah is {get_current_parashah(lang='eng')}")


def test_parashah_heb(mocker):
    spy, notification_status = base_flow(mocker, "מה פרשת השבוע?")
    spy.assert_called_once_with(to_status=notification_status,
                                status=f"פרשת השבוע היא פרשת {get_current_parashah(lang='heb')}")


def test_unsupported_command(mocker):
    spy, _ = base_flow(mocker, "What's up dude?")
    spy.assert_not_called()
