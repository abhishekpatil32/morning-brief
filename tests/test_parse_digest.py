from morning_brief.core import parse_digest


def test_parse_digest_extracts_entries():
    digest = """
============================================================
AI X NEUROSCIENCE DIGEST -- 2026-05-23
============================================================

1. Test Paper One
   https://arxiv.org/abs/2605.12345
   This is a summary of the first paper.

2. Test Paper Two
   https://pubmed.ncbi.nlm.nih.gov/12345678/
   This is a summary of the second paper.
"""

    entries = parse_digest(digest)

    assert len(entries) == 2
    assert entries[0].num == "1"
    assert entries[0].title == "Test Paper One"
    assert entries[0].url == "https://arxiv.org/abs/2605.12345"
    assert "first paper" in entries[0].summary


def test_parse_digest_returns_empty_list_for_bad_text():
    assert parse_digest("Claude returned something unexpected") == []
