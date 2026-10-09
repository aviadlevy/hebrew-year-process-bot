from hypb.text import keep_end, truncate, utf16_len


def test_utf16_len_counts_what_telegram_counts():
    """Telegram measures messages in UTF-16 code units: an emoji outside the BMP is two."""
    assert utf16_len("abc") == 3
    assert utf16_len("מתי") == 3
    assert utf16_len("😀") == 2
    assert utf16_len("✅") == 1


def test_short_text_is_untouched():
    assert truncate("abc", 5) == "abc"
    assert keep_end("abc", 5) == "abc"


def test_truncate_keeps_the_start_and_counts_the_rest():
    assert truncate("abcdefgh", 3) == "abc... [5 more chars]"


def test_keep_end_keeps_the_end_and_counts_the_rest():
    trimmed = keep_end("a" * 100 + "the end", 50)

    assert trimmed.endswith("the end")
    assert trimmed.startswith("… ")
    assert "earlier characters trimmed\n" in trimmed


def test_keep_end_fits_its_limit_in_utf16_units_including_the_notice():
    for text in ("x" * 10_000, "😀" * 10_000, "a😀" * 5_000):
        assert utf16_len(keep_end(text, 4096)) <= 4096


def test_keep_end_never_splits_a_surrogate_pair():
    trimmed = keep_end("😀" * 100, 51)

    assert trimmed.encode("utf-16-le").decode("utf-16-le") == trimmed
    assert trimmed.endswith("😀")
