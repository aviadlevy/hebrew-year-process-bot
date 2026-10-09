from hypb.text import keep_end, truncate


def test_short_text_is_untouched():
    assert truncate("abc", 5) == "abc"
    assert keep_end("abc", 5) == "abc"


def test_truncate_keeps_the_start_and_counts_the_rest():
    assert truncate("abcdefgh", 3) == "abc... [5 more chars]"


def test_keep_end_keeps_the_end_and_counts_the_rest():
    assert keep_end("abcdefgh", 3) == "… 5 earlier characters trimmed\nfgh"
