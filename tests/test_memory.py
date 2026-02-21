"""Tests for space_hog.memory module."""

import subprocess

from space_hog.memory import remove_login_item


def test_remove_login_item_rejects_invalid_applescript_input(monkeypatch):
    called = {"run": False}

    def fake_run(*args, **kwargs):
        called["run"] = True
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

    monkeypatch.setattr("space_hog.memory.subprocess.run", fake_run)

    result = remove_login_item('Bad"; do shell script "rm -rf /" --')

    assert result == {"success": False, "error": "Invalid app name"}
    assert called["run"] is False


def test_remove_login_item_accepts_valid_name(monkeypatch):
    calls = {}

    def fake_run(*args, **kwargs):
        calls["args"] = args
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

    monkeypatch.setattr("space_hog.memory.subprocess.run", fake_run)
    result = remove_login_item("Safe_App 123")

    assert result["success"] is True
    assert calls["args"][0][2].endswith('login item "Safe_App 123"')
