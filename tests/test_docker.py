"""Tests for space_hog.docker module."""

from space_hog.docker import _parse_size


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
