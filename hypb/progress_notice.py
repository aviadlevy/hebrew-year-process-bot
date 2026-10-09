"""The daily progress job's summary: today's bar, and what each platform did with it."""

from hypb.telegram_message import TelegramMessage, bold, code, escape

_OUTCOME_MARKS = {
    "posted": "✅",
    "skipped": "⏸",
    "seeded": "🌱",
    "failed": "❌",
}


def build_progress_summary(current_state: int, progress_bar: str, outcomes: dict[str, str]) -> TelegramMessage:
    platforms = " · ".join(
        f"{escape(platform.capitalize())} {_OUTCOME_MARKS.get(outcome, '•')} {escape(outcome)}" for platform, outcome in outcomes.items()
    )
    return TelegramMessage("\n".join([f"📊 {bold(f'Year progress · {current_state}%')}", code(progress_bar), platforms]))
