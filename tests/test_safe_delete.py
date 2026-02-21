"""Tests for space_hog.safe_delete module."""

import tempfile
from pathlib import Path
from types import SimpleNamespace

import space_hog.safe_delete as safe_delete
from space_hog.safe_delete import move_to_trash, safe_cleanup, trash_contents


class TestTrashContents:
    """Tests for trash_contents function."""

    def test_skips_symlink_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            real_dir = root / "real"
            real_dir.mkdir()
            (real_dir / "file.txt").write_text("x")

            link_dir = root / "link"
            link_dir.symlink_to(real_dir, target_is_directory=True)

            result = trash_contents(str(root), dry_run=True)

            assert result["items_trashed"] == 1
            assert result["success"] is False
            assert result["errors"] is not None
            assert any("Skipped symlink" in err for err in result["errors"])


class TestMoveToTrash:
    """Tests for move_to_trash function."""

    def test_uses_send2trash(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "sample.txt"
            target.write_text("data")
            called = {}
            recorded = {}

            def fake_send2trash(path):
                called["path"] = path

            def fake_record(item_name, item_type, size_bytes):
                recorded["item_name"] = item_name
                recorded["item_type"] = item_type
                recorded["size_bytes"] = size_bytes

            monkeypatch.setattr(
                safe_delete,
                "send2trash",
                SimpleNamespace(send2trash=fake_send2trash),
            )
            monkeypatch.setattr(safe_delete, "_record_removal", fake_record)
            result = move_to_trash(str(target))

            assert result["success"] is True
            assert called["path"] == str(target)
            assert recorded["item_name"] == "sample.txt"
            assert recorded["item_type"] == "file"

    def test_rejects_symlink(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            real = root / "real.txt"
            real.write_text("data")
            symlink = root / "link.txt"
            symlink.symlink_to(real)

            called = {"send2trash": False}

            def fake_send2trash(path):
                called["send2trash"] = True

            monkeypatch.setattr(
                safe_delete,
                "send2trash",
                SimpleNamespace(send2trash=fake_send2trash),
            )

            result = move_to_trash(str(symlink))
            assert result["success"] is False
            assert "symlink" in result["message"].lower()
            assert called["send2trash"] is False


class TestSafeCleanup:
    """Tests for safe_cleanup dispatcher behavior."""

    def test_rm_glob_uses_trash_contents_and_records_stats(self, monkeypatch):
        calls = {"trash_contents": None, "record_cleanup": None}

        def fake_trash_contents(directory, dry_run=False):
            calls["trash_contents"] = (directory, dry_run)
            return {
                "success": True,
                "message": "ok",
                "bytes_freed": 1234,
                "bytes_freed_human": "1.2 KB",
                "items_trashed": 1,
                "errors": None,
                "dry_run": dry_run,
            }

        def fake_record_cleanup(description, bytes_freed, category="manual"):
            calls["record_cleanup"] = (description, bytes_freed, category)

        monkeypatch.setattr(safe_delete, "trash_contents", fake_trash_contents)
        monkeypatch.setattr("space_hog.stats.record_cleanup", fake_record_cleanup)

        result = safe_cleanup(
            command="rm -rf ~/Library/Caches/*",
            description="Caches",
            category="cache",
        )

        assert result["success"] is True
        assert calls["trash_contents"] == (str(Path("~/Library/Caches").expanduser()), False)
        assert calls["record_cleanup"] == ("Caches", 1234, "cache")

    def test_non_rm_delegates_to_run_cleanup(self, monkeypatch):
        calls = {}

        def fake_run_cleanup(command, description, category="manual"):
            calls["args"] = (command, description, category)
            return {"success": True, "bytes_freed": 0, "bytes_freed_human": "0.0 B", "error": None, "command": command, "recorded": False}

        monkeypatch.setattr("space_hog.stats.run_cleanup", fake_run_cleanup)

        result = safe_cleanup("docker system prune -a", "Docker", category="docker")
        assert result["success"] is True
        assert calls["args"] == ("docker system prune -a", "Docker", "docker")
