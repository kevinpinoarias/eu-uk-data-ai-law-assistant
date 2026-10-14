"""Parsed documents are stored as JSON Lines, one provision per line, and read back unchanged."""

from __future__ import annotations

import json

from law_assistant.model import Provision
from law_assistant.parse.store import read_jsonl, write_jsonl


def _p(i: int, text: str) -> Provision:
    return Provision(
        id=f"eu-test/art-{i}",
        instrument="eu-test",
        jurisdiction="EU",
        language="es",
        version="oj",
        unit="article",
        kind="article",
        path=(str(i),),
        text=text,
        order=i,
        heading="Título",
    )


def test_provisions_round_trip_through_a_jsonl_file(tmp_path):
    original = [_p(1, "Artículo con ñ y «comillas»"), _p(2, "otro")]
    path = tmp_path / "nested" / "doc.jsonl"
    write_jsonl(path, original)
    assert read_jsonl(path) == original


def test_the_file_has_one_json_object_per_line_and_keeps_accents_readable(tmp_path):
    path = tmp_path / "doc.jsonl"
    write_jsonl(path, [_p(1, "ñ"), _p(2, "b")])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["text"] == "ñ"
    assert "ñ" in lines[0]  # not escaped as ñ
