"""Tests for backup service."""

import sqlite3
import time
from pathlib import Path

import pytest

from html_tool_manager.core.backup import (
    BACKUP_FILENAME_PATTERN,
    BackupError,
    BackupInfo,
    BackupNotFoundError,
    BackupService,
    InvalidFilenameError,
)


def _create_test_database(db_path: Path) -> None:
    """Create a simple SQLite database for testing."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO test (value) VALUES ('test data')")
        conn.commit()


@pytest.fixture
def backup_service(tmp_path: Path) -> BackupService:
    """Create a BackupService with temporary directories."""
    db_path = tmp_path / "test.db"
    _create_test_database(db_path)
    backup_dir = tmp_path / "backups"
    return BackupService(str(db_path), str(backup_dir), max_generations=3)


class TestBackupFilenamePattern:
    """Tests for backup filename validation pattern."""

    def test_valid_filename(self) -> None:
        """Valid filename should match pattern."""
        assert BACKUP_FILENAME_PATTERN.match("tools_20250114_153042.db")

    def test_invalid_filename_no_prefix(self) -> None:
        """Filename without tools_ prefix should not match."""
        assert not BACKUP_FILENAME_PATTERN.match("backup_20250114_153042.db")

    def test_invalid_filename_wrong_format(self) -> None:
        """Filename with wrong date format should not match."""
        assert not BACKUP_FILENAME_PATTERN.match("tools_2025-01-14_15:30:42.db")

    def test_invalid_filename_wrong_extension(self) -> None:
        """Filename with wrong extension should not match."""
        assert not BACKUP_FILENAME_PATTERN.match("tools_20250114_153042.sqlite")


class TestBackupInfo:
    """Tests for BackupInfo class."""

    def test_size_human_bytes(self, tmp_path: Path) -> None:
        """File size in bytes should display correctly."""
        info = BackupInfo(
            filename="test.db",
            filepath=tmp_path / "test.db",
            created_at=None,  # type: ignore[arg-type]
            size_bytes=500,
        )
        assert "500.0 B" == info.size_human

    def test_size_human_kilobytes(self, tmp_path: Path) -> None:
        """File size in KB should display correctly."""
        info = BackupInfo(
            filename="test.db",
            filepath=tmp_path / "test.db",
            created_at=None,  # type: ignore[arg-type]
            size_bytes=2048,
        )
        assert "2.0 KB" == info.size_human

    def test_size_human_megabytes(self, tmp_path: Path) -> None:
        """File size in MB should display correctly."""
        info = BackupInfo(
            filename="test.db",
            filepath=tmp_path / "test.db",
            created_at=None,  # type: ignore[arg-type]
            size_bytes=5 * 1024 * 1024,
        )
        assert "5.0 MB" == info.size_human


class TestBackupServiceCreateBackup:
    """Tests for BackupService.create_backup method."""

    def test_create_backup_success(self, backup_service: BackupService) -> None:
        """Backup should be created successfully."""
        result = backup_service.create_backup()

        assert result.filename.startswith("tools_")
        assert result.filename.endswith(".db")
        assert result.filepath.exists()
        assert result.size_bytes > 0

    def test_create_backup_creates_directory(self, backup_service: BackupService) -> None:
        """Backup directory should be created if it doesn't exist."""
        assert not backup_service.backup_dir.exists()
        backup_service.create_backup()
        assert backup_service.backup_dir.exists()

    def test_create_backup_filename_format(self, backup_service: BackupService) -> None:
        """Backup filename should match expected pattern."""
        result = backup_service.create_backup()
        assert BACKUP_FILENAME_PATTERN.match(result.filename)

    def test_create_backup_copies_content(self, backup_service: BackupService) -> None:
        """Backup file should have the same content as original."""
        result = backup_service.create_backup()
        # Verify SQLite database content matches
        with sqlite3.connect(str(backup_service.db_path)) as orig:
            orig_data = orig.execute("SELECT * FROM test").fetchall()
        with sqlite3.connect(str(result.filepath)) as backup:
            backup_data = backup.execute("SELECT * FROM test").fetchall()
        assert orig_data == backup_data

    def test_create_backup_fails_if_db_missing(self, tmp_path: Path) -> None:
        """Backup should fail if database file doesn't exist."""
        service = BackupService(
            str(tmp_path / "nonexistent.db"),
            str(tmp_path / "backups"),
            max_generations=3,
        )
        with pytest.raises(BackupError):
            service.create_backup()


class TestBackupServiceListBackups:
    """Tests for BackupService.list_backups method."""

    def test_list_backups_empty(self, backup_service: BackupService) -> None:
        """List should be empty when no backups exist."""
        result = backup_service.list_backups()
        assert result == []

    def test_list_backups_returns_backups(self, backup_service: BackupService) -> None:
        """List should contain created backups."""
        backup_service.create_backup()
        result = backup_service.list_backups()
        assert len(result) == 1

    def test_list_backups_sorted_by_date(self, backup_service: BackupService) -> None:
        """Backups should be sorted by date, newest first."""
        backup_service.create_backup()
        time.sleep(1.1)  # Ensure different timestamps (filename uses seconds)
        backup_service.create_backup()

        result = backup_service.list_backups()
        assert len(result) == 2
        assert result[0].created_at >= result[1].created_at

    def test_list_backups_ignores_invalid_files(self, backup_service: BackupService) -> None:
        """List should ignore files that don't match the pattern."""
        backup_service.backup_dir.mkdir(parents=True)
        (backup_service.backup_dir / "invalid_backup.db").write_text("test")
        (backup_service.backup_dir / "tools_20250114_153042.db").write_text("valid")

        result = backup_service.list_backups()
        assert len(result) == 1
        assert result[0].filename == "tools_20250114_153042.db"


class TestBackupServiceRotation:
    """Tests for backup rotation functionality."""

    def test_rotation_removes_old_backups(self, backup_service: BackupService) -> None:
        """Old backups should be removed when max_generations is exceeded."""
        # Create backup files directly with different timestamps to avoid waiting
        backup_service.backup_dir.mkdir(parents=True)
        filenames = [
            "tools_20250101_000001.db",
            "tools_20250101_000002.db",
            "tools_20250101_000003.db",
            "tools_20250101_000004.db",
            "tools_20250101_000005.db",
        ]
        for filename in filenames:
            (backup_service.backup_dir / filename).write_text("test")

        # Create one more backup which should trigger rotation
        backup_service.create_backup()

        result = backup_service.list_backups()
        # max_generations is 3, so only 3 should remain
        assert len(result) == 3


class TestBackupServiceRestore:
    """Tests for BackupService.restore_backup method."""

    def test_restore_backup_success(self, backup_service: BackupService) -> None:
        """Restore should succeed with valid backup."""
        # Create a backup
        backup = backup_service.create_backup()

        # Modify the original database
        with sqlite3.connect(str(backup_service.db_path)) as conn:
            conn.execute("UPDATE test SET value = 'modified data' WHERE id = 1")
            conn.commit()

        # Verify modification
        with sqlite3.connect(str(backup_service.db_path)) as conn:
            modified_data = conn.execute("SELECT value FROM test WHERE id = 1").fetchone()
        assert modified_data[0] == "modified data"

        # Restore from backup
        result = backup_service.restore_backup(backup.filename)

        assert result is True
        # Verify original data is restored
        with sqlite3.connect(str(backup_service.db_path)) as conn:
            restored_data = conn.execute("SELECT value FROM test WHERE id = 1").fetchone()
        assert restored_data[0] == "test data"

    def test_restore_backup_not_found(self, backup_service: BackupService) -> None:
        """Restore should fail with nonexistent backup."""
        backup_service.backup_dir.mkdir(parents=True)
        with pytest.raises(BackupNotFoundError):
            backup_service.restore_backup("tools_20250114_153042.db")

    def test_restore_invalid_filename_path_traversal(self, backup_service: BackupService) -> None:
        """Restore should reject path traversal attempts."""
        with pytest.raises(InvalidFilenameError):
            backup_service.restore_backup("../../../etc/passwd")

    def test_restore_invalid_filename_slash(self, backup_service: BackupService) -> None:
        """Restore should reject filenames with slashes."""
        with pytest.raises(InvalidFilenameError):
            backup_service.restore_backup("subdir/tools_20250114_153042.db")

    def test_restore_invalid_filename_pattern(self, backup_service: BackupService) -> None:
        """Restore should reject filenames that don't match pattern."""
        with pytest.raises(InvalidFilenameError):
            backup_service.restore_backup("malicious.db")


class TestBackupServiceDelete:
    """Tests for BackupService.delete_backup method."""

    def test_delete_backup_success(self, backup_service: BackupService) -> None:
        """Delete should succeed with valid backup."""
        backup = backup_service.create_backup()
        assert backup.filepath.exists()

        result = backup_service.delete_backup(backup.filename)

        assert result is True
        assert not backup.filepath.exists()

    def test_delete_backup_not_found(self, backup_service: BackupService) -> None:
        """Delete should fail with nonexistent backup."""
        backup_service.backup_dir.mkdir(parents=True)
        with pytest.raises(BackupNotFoundError):
            backup_service.delete_backup("tools_20250114_153042.db")

    def test_delete_invalid_filename(self, backup_service: BackupService) -> None:
        """Delete should reject invalid filenames."""
        with pytest.raises(InvalidFilenameError):
            backup_service.delete_backup("../malicious.db")


class TestBackupServiceValidateFilename:
    """Tests for filename validation."""

    def test_validate_valid_filename(self, backup_service: BackupService) -> None:
        """Valid filename should pass validation."""
        # Should not raise
        backup_service._validate_filename("tools_20250114_153042.db")

    def test_validate_path_traversal_dotdot(self, backup_service: BackupService) -> None:
        """Path traversal with .. should be rejected."""
        with pytest.raises(InvalidFilenameError, match="path traversal"):
            backup_service._validate_filename("..tools_20250114_153042.db")

    def test_validate_path_traversal_forward_slash(self, backup_service: BackupService) -> None:
        """Path traversal with / should be rejected."""
        with pytest.raises(InvalidFilenameError, match="path traversal"):
            backup_service._validate_filename("foo/tools_20250114_153042.db")

    def test_validate_path_traversal_backslash(self, backup_service: BackupService) -> None:
        r"""Path traversal with \\ should be rejected."""
        with pytest.raises(InvalidFilenameError, match="path traversal"):
            backup_service._validate_filename("foo\\tools_20250114_153042.db")

    def test_validate_invalid_pattern(self, backup_service: BackupService) -> None:
        """Filename not matching pattern should be rejected."""
        with pytest.raises(InvalidFilenameError, match="must match"):
            backup_service._validate_filename("random_file.db")
