from pathlib import Path

from morning_brief.dedup import extract_urls, normalize_url, record


def test_normalize_arxiv_version_suffix():
    assert (
        normalize_url("https://arxiv.org/abs/2605.12345v2")
        == "https://arxiv.org/abs/2605.12345"
    )


def test_extract_urls_deduplicates_within_text():
    text = """
    First: https://arxiv.org/abs/2605.12345v1
    Second: https://arxiv.org/abs/2605.12345v2
    """
    assert extract_urls(text) == ["https://arxiv.org/abs/2605.12345"]


def test_record_only_adds_new_urls(tmp_path: Path):
    seen = tmp_path / "seen.txt"

    added = record(seen, ["https://example.com/a", "https://example.com/b"])
    assert added == 2

    added_again = record(seen, ["https://example.com/a", "https://example.com/c"])
    assert added_again == 1

    assert seen.read_text().splitlines() == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]
