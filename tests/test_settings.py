"""
Tests for the project settings: every fetcher must identify itself with a User-Agent (legislation.gov.uk
requires it), the downloaded source documents must stay out of git, and the version number lives in one place.
"""

from __future__ import annotations

import os
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


def test_an_env_file_sets_variables_and_skips_comments_blanks_and_empty_values(tmp_path, monkeypatch):
    for name in ("LAW_TEST_A", "LAW_TEST_B", "LAW_TEST_EMPTY"):
        monkeypatch.delenv(name, raising=False)
    env = tmp_path / ".env"
    env.write_text(
        '# a comment\n\nLAW_TEST_A=one\nLAW_TEST_B = "two words"\nLAW_TEST_EMPTY=\n', encoding="utf-8"
    )
    settings.load_env_file(env)
    assert os.environ["LAW_TEST_A"] == "one"
    assert os.environ["LAW_TEST_B"] == "two words"
    assert "LAW_TEST_EMPTY" not in os.environ
    for name in ("LAW_TEST_A", "LAW_TEST_B"):
        monkeypatch.delenv(name)


def test_an_env_file_never_overrides_a_variable_that_is_already_set(tmp_path, monkeypatch):
    monkeypatch.setenv("LAW_TEST_A", "from-the-shell")
    env = tmp_path / ".env"
    env.write_text("LAW_TEST_A=from-the-file\n", encoding="utf-8")
    settings.load_env_file(env)
    assert os.environ["LAW_TEST_A"] == "from-the-shell"


def test_a_missing_env_file_is_fine(tmp_path):
    settings.load_env_file(tmp_path / "nope.env")


def test_the_package_version_matches_pyproject():
    with (settings.PROJECT_ROOT / "pyproject.toml").open("rb") as f:
        assert tomllib.load(f)["project"]["version"] == law_assistant.__version__


def test_parsed_documents_live_in_a_folder_git_ignores():
    assert settings.PARSED_DIR == settings.PROJECT_ROOT / "data" / "parsed"
    ignored = (settings.PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "data/parsed/" in ignored
