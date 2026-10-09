"""How a mention ended, and how each ending reads on its card.

One class per outcome, each owning its own header detail and extra lines, so
the card renders any outcome the same way instead of switching on which one it
got.
"""

from dataclasses import dataclass

from hypb.alert_messages import error_line, format_traceback
from hypb.telegram_message import quote


class MentionOutcome:
    """The shared shape: an emoji and title for the header, then outcome-specific detail."""

    emoji: str
    title: str

    def detail(self, status) -> str | None:
        """Shown after the title; by default, who could see the toot."""
        return status.get("visibility")

    def lines(self) -> list[str]:
        """HTML lines that follow the question."""
        return []

    def details(self) -> str | None:
        """Raw text for the card's collapsed quote."""
        return None


@dataclass(frozen=True)
class Replied(MentionOutcome):
    reply_text: str
    emoji = "✅"
    title = "Replied"

    def lines(self) -> list[str]:
        return [quote(f"🤖 {self.reply_text}")]


@dataclass(frozen=True)
class NoKeyword(MentionOutcome):
    emoji = "💤"
    title = "No keyword matched"


@dataclass(frozen=True)
class Skipped(MentionOutcome):
    age_minutes: int
    emoji = "⏭"
    title = "Skipped"

    def detail(self, status) -> str | None:
        return f"{self.age_minutes} min old"


@dataclass(frozen=True)
class Failed(MentionOutcome):
    error: BaseException
    emoji = "❌"
    title = "Reply failed"

    def lines(self) -> list[str]:
        return [error_line(self.error)]

    def details(self) -> str | None:
        return format_traceback(self.error)
