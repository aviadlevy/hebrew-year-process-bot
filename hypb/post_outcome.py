"""What the progress job did on one platform in one run."""

from enum import StrEnum


class PostOutcome(StrEnum):
    POSTED = "posted"
    SKIPPED = "skipped"
    SEEDED = "seeded"
    FAILED = "failed"
