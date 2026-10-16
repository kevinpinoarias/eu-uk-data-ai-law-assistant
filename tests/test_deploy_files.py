"""
The deployment files that cannot be run here (no cloud account yet): the data bundle that lets CI build the image
from a clean checkout, and the manual deploy workflow. These tests check what can be checked without a cloud:
the bundle holds exactly what the Dockerfile copies, and the workflow cannot run by accident, asks for the
permissions it needs and no more, and stores no password.
"""

from __future__ import annotations

import importlib.util
import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")


def load_bundle_script():
    spec = importlib.util.spec_from_file_location(
        "make_data_bundle", ROOT / "scripts" / "make_data_bundle.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_data(root: Path) -> None:
    (root / "data" / "chunks").mkdir(parents=True)
    (root / "data" / "indexes").mkdir(parents=True)
    (root / "data" / "chunks" / "eu-gdpr.jsonl").write_text('{"id": "a"}\n', encoding="utf-8")
    (root / "data" / "chunks" / "manifest.json").write_text("{}", encoding="utf-8")
    (root / "data" / "indexes" / "bge-m3.f32").write_bytes(b"\x00" * 16)
    (root / "data" / "indexes" / "bge-m3.keys.json").write_text("[]", encoding="utf-8")
    (root / "data" / "indexes" / "gemini-embedding-2.f32").write_bytes(b"\x00")  # not needed by the service
    (root / "NOTICE").write_text("credits", encoding="utf-8")  # the texts travel with their credit lines


def test_the_bundle_holds_what_the_dockerfile_copies_and_nothing_else(tmp_path):
    fake_data(tmp_path)
    out = tmp_path / "dist" / "data-bundle.zip"
    load_bundle_script().make_bundle(tmp_path, out)
    names = set(zipfile.ZipFile(out).namelist())
    assert names == {
        "NOTICE",
        "data/chunks/eu-gdpr.jsonl",
        "data/chunks/manifest.json",
        "data/indexes/bge-m3.f32",
        "data/indexes/bge-m3.keys.json",
    }


def test_the_bundle_refuses_to_build_without_the_saved_vectors(tmp_path):
    fake_data(tmp_path)
    (tmp_path / "data" / "indexes" / "bge-m3.f32").unlink()
    with pytest.raises(FileNotFoundError, match=r"bge-m3\.f32"):
        load_bundle_script().make_bundle(tmp_path, tmp_path / "out.zip")


def test_the_dockerfile_copies_exactly_the_paths_the_bundle_provides():
    copied = set(re.findall(r"^COPY (data/\S+)", DOCKERFILE, re.MULTILINE))
    assert copied == {"data/chunks", "data/indexes/bge-m3.f32"}
    assert "data/indexes/bge-m3.keys.json" in DOCKERFILE  # the same COPY line, listed with its partner


def test_the_deploy_workflow_runs_only_when_started_by_hand():
    on_block = WORKFLOW.split("jobs:")[0]
    assert "workflow_dispatch" in on_block
    assert not re.search(r"^\s+(push|pull_request|schedule|release):", on_block, re.MULTILINE)


def test_the_deploy_workflow_asks_for_the_permissions_it_needs_and_no_more():
    perms = dict(re.findall(r"^\s{6}(\w[\w-]*): (read|write)$", WORKFLOW, re.MULTILINE))
    assert perms.get("id-token") == "write"  # keyless sign-in to the cloud
    assert perms.get("packages") == "write"  # push the image to the GitHub registry
    assert perms.get("contents") == "read"
    assert set(perms) <= {"id-token", "packages", "contents"}


def test_the_deploy_workflow_stores_no_password_or_key():
    assert "azure/login@" in WORKFLOW and "client-id" in WORKFLOW
    assert not re.search(
        r"(?i)AZURE_CREDENTIALS|client-secret|password:\s*\$\{\{\s*secrets\.(?!GITHUB_TOKEN)", WORKFLOW
    )
    assert (
        "GEMINI_API_KEY" not in WORKFLOW
    )  # the model key lives in the host, never in the image or the workflow


def test_every_action_is_pinned_to_a_version():
    uses = re.findall(r"uses:\s*(\S+)", WORKFLOW)
    assert uses and all("@v" in u for u in uses), uses
