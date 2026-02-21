"""Tests for space_hog.scanners module."""

import tempfile
from pathlib import Path

from space_hog.scanners import find_large_files, find_space_hogs, hash_file


class TestFindLargeFiles:
    """Tests for find_large_files function."""

    def test_no_large_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create small files
            (Path(tmpdir) / "small.txt").write_text("small")

            large_files = list(find_large_files(Path(tmpdir), min_size_mb=1))
            assert len(large_files) == 0

    def test_finds_large_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file just over 1MB
            large_file = Path(tmpdir) / "large.bin"
            large_file.write_bytes(b"x" * (1024 * 1024 + 100))

            large_files = list(find_large_files(Path(tmpdir), min_size_mb=1))
            assert len(large_files) == 1
            assert large_files[0].path == large_file

    def test_respects_min_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files of different sizes
            (Path(tmpdir) / "1mb.bin").write_bytes(b"x" * (1024 * 1024))
            (Path(tmpdir) / "2mb.bin").write_bytes(b"x" * (2 * 1024 * 1024))

            # Should only find 2mb file with min_size=2
            large_files = list(find_large_files(Path(tmpdir), min_size_mb=2))
            assert len(large_files) == 1
            assert "2mb" in large_files[0].path.name


class TestFindSpaceHogs:
    """Tests for find_space_hogs function."""

    def test_finds_node_modules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create node_modules with enough size
            node_modules = Path(tmpdir) / "project" / "node_modules"
            node_modules.mkdir(parents=True)

            # Add some content to make it sizeable
            for i in range(100):
                (node_modules / f"file{i}.txt").write_text("x" * 1000)

            hogs = find_space_hogs(Path(tmpdir), min_size_mb=0)
            hog_names = [h[2] for h in hogs]
            assert "Node.js dependencies" in hog_names

    def test_finds_git_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .git directory
            git_dir = Path(tmpdir) / "repo" / ".git"
            git_dir.mkdir(parents=True)

            # Add content
            for i in range(50):
                (git_dir / f"obj{i}").write_text("x" * 2000)

            hogs = find_space_hogs(Path(tmpdir), min_size_mb=0)
            hog_names = [h[2] for h in hogs]
            assert "Git repositories" in hog_names

    def test_skips_symlinked_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            real_node_modules = root / "real_node_modules"
            real_node_modules.mkdir()
            (real_node_modules / "file.txt").write_text("x" * 1000)

            symlinked = root / "project" / "node_modules"
            symlinked.parent.mkdir()
            symlinked.symlink_to(real_node_modules, target_is_directory=True)

            hogs = find_space_hogs(root, min_size_mb=0)
            hog_paths = [h[0] for h in hogs]
            assert symlinked not in hog_paths

    def test_finds_space_hogs_in_independent_branches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            node_modules = root / "project_a" / "node_modules"
            git_dir = root / "project_b" / ".git"
            node_modules.mkdir(parents=True)
            git_dir.mkdir(parents=True)
            (node_modules / "dep").write_text("x" * 5000)
            (git_dir / "obj").write_text("x" * 5000)

            hogs = find_space_hogs(root, min_size_mb=0)
            hog_descriptions = [h[2] for h in hogs]
            assert "Node.js dependencies" in hog_descriptions
            assert "Git repositories" in hog_descriptions


class TestHashFile:
    """Tests for hash_file function."""

    def test_consistent_hash(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()

            hash1 = hash_file(Path(f.name))
            hash2 = hash_file(Path(f.name))

            assert hash1 == hash2

    def test_different_content_different_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"

            file1.write_text("content one")
            file2.write_text("content two")

            assert hash_file(file1) != hash_file(file2)

    def test_same_content_same_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"

            file1.write_text("identical content")
            file2.write_text("identical content")

            assert hash_file(file1) == hash_file(file2)
