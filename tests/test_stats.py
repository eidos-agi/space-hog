"""Tests for space_hog.stats module."""

import subprocess
from types import SimpleNamespace

from space_hog.stats import run_cleanup


def test_run_cleanup_executes_without_shell(monkeypatch):
    calls = {}

    def fake_run(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

    monkeypatch.setattr("space_hog.stats.subprocess.run", fake_run)
    monkeypatch.setattr(
        "space_hog.stats.shutil.disk_usage",
        lambda _: SimpleNamespace(total=1, used=1, free=1),
    )

    result = run_cleanup("echo hello", "test cleanup")

    assert result["success"] is True
    assert calls["args"][0] == ["echo", "hello"]
    assert calls["kwargs"]["shell"] is False

