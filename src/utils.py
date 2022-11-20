async def send_async_slack_alert(sc, msg):
    await sc.chat_postMessage(
        channel="#hebrew-year-process",
        text=msg
    )


def send_slack_alert(sc, msg):
    sc.chat_postMessage(
        channel="#hebrew-year-process",
        text=msg
    )
