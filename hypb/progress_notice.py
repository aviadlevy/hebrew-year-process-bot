"""The daily progress job's summary: today's bar, and what each platform did with it."""

from hypb.post_outcome import PostOutcome
from hypb.telegram_message import TelegramMessage, bold, escape

_OUTCOME_MARKS = {
    PostOutcome.POSTED: "✅",
    PostOutcome.SKIPPED: "⏸",
    PostOutcome.SEEDED: "🌱",
    PostOutcome.FAILED: "❌",
}


def build_progress_summary(current_state: int, progress_bar: str, outcomes: dict[str, PostOutcome]) -> TelegramMessage:
    # Plain text, not monospace: Telegram's code font draws `░` as a solid block.
    # The percentage the bar ends with is already in the title.
    bar = progress_bar.removesuffix(f" {current_state}%")
    platforms = " · ".join(f"{escape(platform.capitalize())} {_OUTCOME_MARKS[outcome]} {outcome}" for platform, outcome in outcomes.items())
    return TelegramMessage("\n".join([f"📊 {bold(f'Year progress · {current_state}%')}", escape(bar), platforms]))
