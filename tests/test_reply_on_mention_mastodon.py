import random

import slack
from mastodon import Mastodon

from src.dates_helper import get_current_date, get_current_parashah
from stream_listener_mastodon import _StreamingListener


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


def base_flow(mocker, message):
    mastodon: Mastodon = Mastodon()
    mocker.patch.object(mastodon, "status_reply")
    spy = mocker.spy(mastodon, "status_reply")
    slack_client: slack.WebClient = slack.WebClient()
    spy_slack = mocker.patch.object(slack_client, "chat_postMessage")
    stream_client = _StreamingListener(mastodon, slack_client)
    status_id = random.randint(0, 100)
    notification = create_notification(message, status_id)
    stream_client.on_notification(notification)
    return spy, spy_slack, notification["status"]


def test_date(mocker):
    spy, spy_slack, notification_status = base_flow(mocker, "What's the date?")
    spy.assert_called_once_with(to_status=notification_status, status=f"The date is:\n{get_current_date(lang='eng')}")
    spy_slack.assert_not_called()


def test_date_heb(mocker):
    spy, spy_slack, notification_status = base_flow(mocker, "מה התאריך?")
    spy.assert_called_once_with(to_status=notification_status, status=f"התאריך הוא:\n{get_current_date(lang='heb')}")
    spy_slack.assert_not_called()


def test_parashah(mocker):
    spy, spy_slack, notification_status = base_flow(mocker, "What's the parashah?")
    spy.assert_called_once_with(to_status=notification_status,
                                status=f"The Parashah is {get_current_parashah(lang='eng')}")
    spy_slack.assert_not_called()


def test_parashah_heb(mocker):
    spy, spy_slack, notification_status = base_flow(mocker, "מה פרשת השבוע?")
    spy.assert_called_once_with(to_status=notification_status,
                                status=f"פרשת השבוע היא פרשת {get_current_parashah(lang='heb')}")
    spy_slack.assert_not_called()


def test_unsupported_command(mocker):
    spy, spy_slack, notification_status = base_flow(mocker, "What's up dude?")
    spy.assert_not_called()
    spy_slack.assert_not_called()


def test_error_notifies_slack(mocker):
    spy, spy_slack, notification_status = base_flow(mocker, None)
    spy.assert_not_called()
    assert spy_slack.call_count == 1
    assert spy_slack.call_args[1]["channel"] == "#hebrew-year-process"
    assert "exception" in spy_slack.call_args[1]["text"]
