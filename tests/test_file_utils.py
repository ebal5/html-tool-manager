"""Tests for file utility functions."""

import os
import stat
import tempfile
from unittest.mock import patch

import pytest

from html_tool_manager.core.file_utils import atomic_write_file


class TestAtomicWriteFile:
    """Tests for atomic_write_file function."""

    def test_writes_content_correctly(self, tmp_path):
        """Test that content is written correctly."""
        filepath = tmp_path / "test.txt"
        content = "Hello, World!"

        atomic_write_file(str(filepath), content)

        assert filepath.read_text(encoding="utf-8") == content

    def test_writes_unicode_content(self, tmp_path):
        """Test that unicode content is written correctly."""
        filepath = tmp_path / "test.txt"
        content = "こんにちは世界！日本語テスト"

        atomic_write_file(str(filepath), content)

        assert filepath.read_text(encoding="utf-8") == content

    def test_overwrites_existing_file(self, tmp_path):
        """Test that existing file is overwritten."""
        filepath = tmp_path / "test.txt"
        filepath.write_text("old content", encoding="utf-8")

        atomic_write_file(str(filepath), "new content")

        assert filepath.read_text(encoding="utf-8") == "new content"

    def test_sets_default_permissions(self, tmp_path):
        """Test that default file permissions are set correctly."""
        filepath = tmp_path / "test.txt"

        atomic_write_file(str(filepath), "content")

        # Check file permissions (ignore extra bits like sticky bit)
        file_mode = stat.S_IMODE(os.stat(filepath).st_mode)
        assert file_mode == 0o644

    def test_sets_custom_permissions(self, tmp_path):
        """Test that custom file permissions are set correctly."""
        filepath = tmp_path / "test.txt"

        atomic_write_file(str(filepath), "content", mode=0o600)

        file_mode = stat.S_IMODE(os.stat(filepath).st_mode)
        assert file_mode == 0o600

    def test_cleans_up_temp_file_on_write_error(self, tmp_path):
        """Test that temp file is cleaned up when write fails."""
        filepath = tmp_path / "test.txt"

        with patch("os.fdopen") as mock_fdopen:
            mock_fdopen.side_effect = IOError("Write failed")
            with pytest.raises(IOError):
                atomic_write_file(str(filepath), "content")

        # Verify no temp files remain
        remaining_files = list(tmp_path.iterdir())
        assert len(remaining_files) == 0

    def test_cleans_up_temp_file_on_chmod_error(self, tmp_path):
        """Test that temp file is cleaned up when chmod fails."""
        filepath = tmp_path / "test.txt"

        with patch("os.chmod") as mock_chmod:
            mock_chmod.side_effect = OSError("chmod failed")
            with pytest.raises(OSError):
                atomic_write_file(str(filepath), "content")

        # Verify no temp files remain
        remaining_files = list(tmp_path.iterdir())
        assert len(remaining_files) == 0

    def test_atomic_replacement(self, tmp_path):
        """Test that file replacement is atomic (uses os.replace)."""
        filepath = tmp_path / "test.txt"
        filepath.write_text("original", encoding="utf-8")

        with patch("os.replace") as mock_replace:
            # Let the real replace happen
            mock_replace.side_effect = lambda src, dst: os.rename(src, dst)
            atomic_write_file(str(filepath), "new content")

            # Verify os.replace was called
            mock_replace.assert_called_once()

    def test_temp_file_created_in_same_directory(self, tmp_path):
        """Test that temp file is created in the same directory as target."""
        filepath = tmp_path / "test.txt"

        # Create a real temp file for the test before patching
        real_fd, real_path = tempfile.mkstemp(dir=str(tmp_path), text=True)

        with patch("html_tool_manager.core.file_utils.tempfile.mkstemp") as mock_mkstemp:
            mock_mkstemp.return_value = (real_fd, real_path)

            atomic_write_file(str(filepath), "content")

            # Verify mkstemp was called with correct directory
            mock_mkstemp.assert_called_once_with(dir=str(tmp_path), text=True)

    def test_raises_permission_error(self, tmp_path):
        """Test that PermissionError is raised when directory is not writable."""
        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)

        filepath = readonly_dir / "test.txt"

        try:
            with pytest.raises(PermissionError):
                atomic_write_file(str(filepath), "content")
        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)

    def test_multiline_content(self, tmp_path):
        """Test that multiline content is written correctly."""
        filepath = tmp_path / "test.txt"
        content = """Line 1
Line 2
Line 3
"""

        atomic_write_file(str(filepath), content)

        assert filepath.read_text(encoding="utf-8") == content

    def test_empty_content(self, tmp_path):
        """Test that empty content is written correctly."""
        filepath = tmp_path / "test.txt"

        atomic_write_file(str(filepath), "")

        assert filepath.read_text(encoding="utf-8") == ""

    def test_large_content(self, tmp_path):
        """Test that large content is written correctly."""
        filepath = tmp_path / "test.txt"
        content = "x" * 1_000_000  # 1MB of content

        atomic_write_file(str(filepath), content)

        assert filepath.read_text(encoding="utf-8") == content
