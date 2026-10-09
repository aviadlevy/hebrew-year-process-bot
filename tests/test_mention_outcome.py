from hypb.mention_outcome import MentionOutcome, OutcomeKind


def test_each_outcome_names_its_kind_and_keeps_its_detail():
    error = RuntimeError("boom")

    assert MentionOutcome.replied("answer") == MentionOutcome(OutcomeKind.REPLIED, reply_text="answer")
    assert MentionOutcome.no_keyword() == MentionOutcome(OutcomeKind.NO_KEYWORD)
    assert MentionOutcome.skipped(age_minutes=31) == MentionOutcome(OutcomeKind.SKIPPED, age_minutes=31)
    assert MentionOutcome.failed(error).error is error

