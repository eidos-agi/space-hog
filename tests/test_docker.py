"""Tests for space_hog.docker module."""

import json
import subprocess

from space_hog.docker import _parse_size, _sanitize_label_text, analyze_docker_volumes, print_docker_analysis


class TestParseSize:
    """Tests for _parse_size function."""

    def test_zero(self):
        assert _parse_size("0B") == 0
        assert _parse_size("") == 0
        assert _parse_size(None) == 0

    def test_bytes(self):
        assert _parse_size("100B") == 100
        assert _parse_size("1024B") == 1024

    def test_kilobytes(self):
        assert _parse_size("1KB") == 1024
        assert _parse_size("1.5KB") == 1536
        assert _parse_size("40.96kB") == 41943  # Case insensitive

    def test_megabytes(self):
        assert _parse_size("1MB") == 1024 * 1024
        assert _parse_size("100MB") == 100 * 1024 * 1024
        assert _parse_size("1.5MB") == int(1.5 * 1024 * 1024)

    def test_gigabytes(self):
        assert _parse_size("1GB") == 1024 * 1024 * 1024
        assert _parse_size("1.592GB") == int(1.592 * 1024 * 1024 * 1024)

    def test_scientific_notation(self):
        # Docker sometimes outputs scientific notation for reclaimable
        assert _parse_size("-4.826e+08B") == 0  # Negative becomes 0
        assert _parse_size("1e+06B") == 1000000
        assert _parse_size("5.5e+09B") == 5500000000

    def test_kib_mib_gib(self):
        assert _parse_size("1KiB") == 1024
        assert _parse_size("1MiB") == 1024 * 1024
        assert _parse_size("1GiB") == 1024 * 1024 * 1024

    def test_plain_number(self):
        assert _parse_size("12345") == 12345


class TestDockerLabelSafety:
    """Tests for Docker label sanitization and command quoting."""

    def test_sanitize_label_text_removes_control_characters(self):
        assert _sanitize_label_text("proj\x00name\x1f") == "projname"
        assert _sanitize_label_text("\n\t") is None

    def test_analyze_docker_volumes_sanitizes_project(self, monkeypatch):
        payload = {
            "Volumes": [
                {
                    "Name": "vol1",
                    "Labels": "com.docker.compose.project=proj\x00evil",
                    "Size": "1KB",
                    "Links": "0",
                    "Driver": "local",
                }
            ]
        }

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=json.dumps(payload), stderr="")

        monkeypatch.setattr("space_hog.docker.subprocess.run", fake_run)
        volumes = analyze_docker_volumes()

        assert len(volumes) == 1
        assert volumes[0]["project"] == "projevil"

    def test_print_docker_analysis_quotes_project_name(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "space_hog.docker.analyze_docker",
            lambda: {
                "installed": True,
                "running": True,
                "vm_disk_path": None,
                "vm_disk_allocated": 0,
                "vm_disk_used": 0,
                "vm_disk_bloat": 0,
                "images": {"count": 0, "size": 0, "reclaimable": 0},
                "containers": {"count": 0, "size": 0, "reclaimable": 0},
                "volumes": {"count": 1, "size": 1024, "reclaimable": 1024},
                "build_cache": {"size": 0, "reclaimable": 0},
                "total_usage": 1024,
                "total_reclaimable": 1024,
            },
        )
        monkeypatch.setattr(
            "space_hog.docker.analyze_docker_volumes",
            lambda: [
                {
                    "name": "vol1",
                    "project": "my project",
                    "size": 1024,
                    "size_human": "1.0 KB",
                    "links": 0,
                    "in_use": False,
                    "driver": "local",
                }
            ],
        )

        print_docker_analysis()
        out = capsys.readouterr().out
        assert "label=com.docker.compose.project='my project'" in out
