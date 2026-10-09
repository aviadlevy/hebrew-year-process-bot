"""How a mention ended, with whatever detail the notice needs to show for it."""

from dataclasses import dataclass
from enum import Enum


class OutcomeKind(Enum):
    REPLIED = "replied"
    NO_KEYWORD = "no_keyword"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class MentionOutcome:
    kind: OutcomeKind
    reply_text: str | None = None
    age_minutes: int | None = None
    error: BaseException | None = None

    @classmethod
    def replied(cls, reply_text: str) -> MentionOutcome:
        return cls(OutcomeKind.REPLIED, reply_text=reply_text)

    @classmethod
    def no_keyword(cls) -> MentionOutcome:
        return cls(OutcomeKind.NO_KEYWORD)

    @classmethod
    def skipped(cls, age_minutes: int) -> MentionOutcome:
        return cls(OutcomeKind.SKIPPED, age_minutes=age_minutes)

    @classmethod
    def failed(cls, error: BaseException) -> MentionOutcome:
        return cls(OutcomeKind.FAILED, error=error)
