"""
The deployment files that cannot be run here (no cloud account yet): the data bundle that lets CI build the image
from a clean checkout, the manual deploy workflow for Azure Container Apps and the one-time setup script. These
tests check what can be checked without a cloud: the bundle holds exactly what the Dockerfile copies; the workflow
cannot run by accident, asks for the permissions it needs and no more, stores no password or key, and leaves the
app closed to people without the access code and unable to scale itself into a bill; the script is valid shell,
reads secrets hidden, limits the keyless sign-in to this repository and gives it one resource group only.
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
SETUP = (ROOT / "scripts" / "azure_setup.sh").read_text(encoding="utf-8")


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
    # the model key and the access code are named, never held: the app reads them from its own secret store
    assert all(
        m.group(0).endswith("=secretref:") for m in re.finditer(r"GEMINI_API_KEY=?(?:secretref:)?", WORKFLOW)
    )
    assert "GEMINI_API_KEY=secretref:gemini-key" in WORKFLOW


def test_the_app_stays_closed_to_visitors_without_the_code_and_cannot_scale_into_a_bill():
    # Every deploy re-asserts these, so an app set up carelessly by hand is corrected, or the deploy fails.
    for setting in (
        "ACCESS_CODE=secretref:access-code",
        "--min-replicas 0",
        "--max-replicas 1",
        "--target-port 8000",
    ):
        assert setting in WORKFLOW, setting


def test_the_bundle_is_fetched_with_plain_curl_into_a_folder_made_first_and_listed():
    # The release is public, so no tool or token is needed; a missing folder or tool made the first run fail
    # in two seconds with no visible reason, so the folder is made first and what arrived is listed in the log.
    step = WORKFLOW.split("Fetch and unpack the data bundle")[1].split("docker/setup-buildx-action")[0]
    assert step.index("mkdir -p dist") < step.index("curl ") < step.index("ls -l dist") < step.index("unzip ")
    assert "releases/download/" in step and "gh release" not in step and "GH_TOKEN" not in step
    assert "curl -fsSL" in step  # fail on an HTTP error, follow the redirect, stay quiet
    # The bundle holds NOTICE and the checkout already has one: without -o, unzip stops to ask whether to
    # overwrite it, and nobody can answer in CI (the first real run failed here).
    assert "unzip -q -o" in step


def test_the_setup_script_reads_secrets_hidden_and_is_valid_shell():
    import shutil
    import subprocess

    def working_bash():
        # On Windows `bash` can be the WSL launcher, which fails when no Linux distribution has a shell.
        git_bash = (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe")
        for candidate in (shutil.which("bash"), *git_bash):
            if candidate and Path(candidate).exists():
                probe = subprocess.run([candidate, "-c", "echo ok"], capture_output=True, text=True)
                if probe.returncode == 0 and probe.stdout.strip() == "ok":
                    return candidate
        return None

    assert SETUP.count("read -rsp") >= 2  # the Gemini key and the access code, typed hidden
    assert not re.search(r"echo\s+\"?\$(KEY|CODE|value)", SETUP)  # never echoed
    bash = working_bash()
    if bash is None:
        pytest.skip("no working bash on this machine")
    result = subprocess.run(
        [bash, "-n", str(ROOT / "scripts" / "azure_setup.sh")], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_the_setup_script_limits_the_sign_in_to_this_repository_and_one_resource_group():
    assert "kevinpinoarias/eu-uk-data-ai-law-assistant" in SETUP
    assert "ref:refs/heads/main" in SETUP  # only the main branch can sign in
    assert "--role Contributor" in SETUP and "resourceGroups/" in SETUP  # not the whole subscription
    assert "Owner" not in SETUP
    assert "--min-replicas 0" in SETUP and "--max-replicas 1" in SETUP


def test_every_action_is_pinned_to_a_version():
    uses = re.findall(r"uses:\s*(\S+)", WORKFLOW)
    assert uses and all("@v" in u for u in uses), uses
