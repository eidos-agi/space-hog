"""Tests for space_hog.utils module."""

import tempfile
from pathlib import Path

from space_hog.utils import format_size, get_dir_size, FileInfo


class TestFormatSize:
    """Tests for format_size function."""

    def test_bytes(self):
        assert format_size(0) == "0.0 B"
        assert format_size(100) == "100.0 B"
        assert format_size(1023) == "1023.0 B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"
        assert format_size(10240) == "10.0 KB"

    def test_megabytes(self):
        assert format_size(1024 * 1024) == "1.0 MB"
        assert format_size(1024 * 1024 * 100) == "100.0 MB"

    def test_gigabytes(self):
        assert format_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_size(1024 * 1024 * 1024 * 5) == "5.0 GB"

    def test_terabytes(self):
        assert format_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"


class TestGetDirSize:
    """Tests for get_dir_size function."""

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            size = get_dir_size(Path(tmpdir))
            assert size == 0

    def test_directory_with_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with known size
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("x" * 100)

            size = get_dir_size(Path(tmpdir))
            assert size == 100

    def test_nested_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            (Path(tmpdir) / "file1.txt").write_text("a" * 50)
            (subdir / "file2.txt").write_text("b" * 75)

            size = get_dir_size(Path(tmpdir))
            assert size == 125

    def test_nonexistent_directory(self):
        size = get_dir_size(Path("/nonexistent/path"))
        assert size == 0


class TestFileInfo:
    """Tests for FileInfo dataclass."""

    def test_size_human_property(self):
        info = FileInfo(Path("/test"), 1024 * 1024)
        assert info.size_human == "1.0 MB"

    def test_path_stored(self):
        path = Path("/some/path")
        info = FileInfo(path, 100)
        assert info.path == path
        assert info.size == 100
