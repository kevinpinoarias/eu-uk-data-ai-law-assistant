"""The smoke-test script itself is run as a test, so a break in it shows up in CI and locally."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "smoke_test.py"


def load():
    spec = importlib.util.spec_from_file_location("smoke_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_demo_server_starts_as_a_separate_process_and_passes_every_check():
    assert load().run() == []


def test_a_server_that_does_not_start_is_reported_not_hung(monkeypatch):
    module = load()
    monkeypatch.setattr(module, "ROOT_PYTHON", module.sys.executable)
    original = module.subprocess.Popen

    def broken(cmd, **kwargs):
        return original([module.sys.executable, "-c", "raise SystemExit(3)"], **kwargs)

    monkeypatch.setattr(module.subprocess, "Popen", broken)
    assert module.run(startup_seconds=5) == ["the server starts and /health answers"]
