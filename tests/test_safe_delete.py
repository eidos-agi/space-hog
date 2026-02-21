"""Tests for space_hog.safe_delete module."""

import tempfile
from pathlib import Path
from types import SimpleNamespace

import space_hog.safe_delete as safe_delete
from space_hog.safe_delete import move_to_trash, trash_contents


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

            def fake_send2trash(path):
                called["path"] = path

            monkeypatch.setattr(
                safe_delete,
                "send2trash",
                SimpleNamespace(send2trash=fake_send2trash),
            )
            monkeypatch.setattr(safe_delete, "_record_removal", lambda *args, **kwargs: None)
            result = move_to_trash(str(target))

            assert result["success"] is True
            assert called["path"] == str(target)
