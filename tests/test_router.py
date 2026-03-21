from __future__ import annotations

import pytest

from core.router import route_text


@pytest.mark.parametrize(
    "text, expected_route",
    [
        ("fix the bug in my python function", "code"),
        ("debug this fastapi endpoint", "code"),
        ("refactor this class", "code"),
        ("research the latest papers on transformers", "research"),
        ("summarize these sources", "research"),
        ("explain gradient descent", "research"),
        ("deploy to kubernetes", "ops"),
        ("docker incident on-call alert", "ops"),
        ("what is the meaning of life", "general"),
        ("hello", "general"),
    ],
)
def test_route_text(text: str, expected_route: str) -> None:
    result = route_text(text)
    assert result.route == expected_route
    assert result.input == text
    assert result.rationale
    assert result.timestamp_utc


def test_route_text_empty_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        route_text("")


def test_route_text_whitespace_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        route_text("   ")
