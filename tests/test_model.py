"""The common shape every parser produces: one Provision per recital, article, paragraph, point or annex item."""

from __future__ import annotations

import json

import pytest

from law_assistant.model import Provision


def _provision(**overrides) -> Provision:
    fields = {
        "id": "eu-gdpr/art-6/1/f",
        "instrument": "eu-gdpr",
        "jurisdiction": "EU",
        "language": "en",
        "version": "oj",
        "unit": "article",
        "kind": "point",
        "path": ("6", "1", "f"),
        "text": "processing is necessary for the purposes of the legitimate interests pursued",
        "order": 42,
        "heading": "Lawfulness of processing",
        "chapter": "CHAPTER II — Principles",
    }
    fields.update(overrides)
    return Provision(**fields)


def test_a_provision_survives_a_round_trip_through_json():
    original = _provision()
    again = Provision.from_dict(json.loads(json.dumps(original.to_dict())))
    assert again == original
    assert again.path == ("6", "1", "f")  # a tuple again, not a list


def test_a_provision_cannot_be_changed_after_it_is_built():
    with pytest.raises(AttributeError):
        _provision().text = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("field,value", [("unit", "chapter"), ("kind", "section"), ("jurisdiction", "FR")])
def test_unknown_labels_are_refused(field, value):
    with pytest.raises(ValueError, match=field):
        _provision(**{field: value})


def test_the_path_must_not_be_empty_and_the_text_must_be_text():
    with pytest.raises(ValueError, match="path"):
        _provision(path=())
    with pytest.raises(ValueError, match="text"):
        _provision(text=None)  # type: ignore[arg-type]
