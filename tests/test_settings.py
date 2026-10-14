"""
Tests for the project settings: every fetcher must identify itself with a User-Agent (legislation.gov.uk
requires it), the downloaded source documents must stay out of git, and the version number lives in one place.
"""

from __future__ import annotations

import tomllib

import pytest

import law_assistant
from law_assistant import settings


def test_user_agent_names_the_project_the_version_and_the_contact():
    ua = settings.user_agent("kevin@example.com")
    assert ua.startswith(f"eu-uk-data-ai-law-assistant/{law_assistant.__version__} ")
    assert "kevin@example.com" in ua


def test_user_agent_reads_the_contact_from_the_environment(monkeypatch):
    monkeypatch.setenv("FETCHER_CONTACT", "https://github.com/kevinpinoarias")
    assert "https://github.com/kevinpinoarias" in settings.user_agent()


def test_an_explicit_contact_wins_over_the_environment(monkeypatch):
    monkeypatch.setenv("FETCHER_CONTACT", "env@example.com")
    assert "explicit@example.com" in settings.user_agent("explicit@example.com")


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_a_missing_contact_is_refused_instead_of_sending_an_anonymous_agent(monkeypatch, blank):
    monkeypatch.delenv("FETCHER_CONTACT", raising=False)
    with pytest.raises(ValueError, match="FETCHER_CONTACT"):
        settings.user_agent(blank)


def test_a_contact_with_control_characters_is_refused():
    with pytest.raises(ValueError, match="control"):
        settings.user_agent("kevin@example.com\r\nX-Injected: yes")


def test_raw_source_documents_live_in_a_folder_git_ignores():
    assert settings.RAW_DIR == settings.PROJECT_ROOT / "data" / "raw"
    ignored = (settings.PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "data/raw/" in ignored


def test_the_package_version_matches_pyproject():
    with (settings.PROJECT_ROOT / "pyproject.toml").open("rb") as f:
        assert tomllib.load(f)["project"]["version"] == law_assistant.__version__
