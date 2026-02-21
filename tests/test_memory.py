"""Tests for space_hog.memory module."""

import re
import subprocess

from space_hog.memory import remove_login_item


def test_remove_login_item_sanitizes_applescript_input(monkeypatch):
    calls = {}

    def fake_run(*args, **kwargs):
        calls["args"] = args
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

    monkeypatch.setattr("space_hog.memory.subprocess.run", fake_run)

    result = remove_login_item('Bad"; do shell script "rm -rf /" --')

    assert result["success"] is True
    applescript = calls["args"][0][2]
    embedded_name = re.search(r'login item "(.*)"$', applescript).group(1)
    assert embedded_name == "Bad do shell script rm -rf  --"
