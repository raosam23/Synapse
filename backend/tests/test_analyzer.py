"""Unit tests for analyzer helpers (no live LLM)."""

from app.agents.analyzer import feature_title


def test_feature_title_prefix() -> None:
    """[Feature]: is added once, not duplicated."""
    assert feature_title("User Authentication") == "[Feature]: User Authentication"
    assert feature_title("[Feature]: Cookie JWT") == "[Feature]: Cookie JWT"
