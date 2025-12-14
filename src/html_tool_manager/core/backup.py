"""Database backup service."""

import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Backup filename pattern: tools_YYYYMMDD_HHMMSS.db
BACKUP_FILENAME_PATTERN = re.compile(r"^tools_\d{8}_\d{6}\.db$")


@dataclass
class BackupInfo:
    """Information about a backup file."""

    filename: str
    filepath: Path
    created_at: datetime
    size_bytes: int

    @property
    def size_human(self) -> str:
        """Return human-readable file size."""
        size: float = float(self.size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class BackupError(Exception):
    """Base exception for backup operations."""

    pass


class BackupNotFoundError(BackupError):
    """Raised when a backup file is not found."""

    pass


class InvalidFilenameError(BackupError):
    """Raised when a filename is invalid or potentially malicious."""

    pass


class BackupService:
    """Service for database backup and restore operations."""

    def __init__(self, db_path: str, backup_dir: str, max_generations: int):
        """Initialize the backup service.

        Args:
            db_path: Path to the SQLite database file.
            backup_dir: Directory to store backup files.
            max_generations: Maximum number of backup files to keep.

        """
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.max_generations = max_generations

    def create_backup(self) -> BackupInfo:
        """Create a backup of the database.

        Returns:
            BackupInfo with details about the created backup.

        Raises:
            BackupError: If the backup fails.

        """
        # Check if database file exists
        if not self.db_path.exists():
            raise BackupError(f"Database file not found: {self.db_path}")

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"tools_{timestamp}.db"
        backup_path = self.backup_dir / filename

        try:
            # Use SQLite backup API for WAL mode safety
            # This ensures consistent backups even with active connections
            with sqlite3.connect(str(self.db_path)) as src:
                with sqlite3.connect(str(backup_path)) as dst:
                    src.backup(dst)

            # Verify backup integrity
            with sqlite3.connect(str(backup_path)) as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()
                if result[0] != "ok":
                    backup_path.unlink()
                    raise BackupError(f"Backup integrity check failed: {result[0]}")

            logger.info("Created backup: %s", filename)

            # Get backup info before rotation
            stat = backup_path.stat()
            backup_info = BackupInfo(
                filename=filename,
                filepath=backup_path,
                created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                size_bytes=stat.st_size,
            )

            # Rotate old backups (after we have the new backup's info)
            self._rotate_backups()

            return backup_info
        except (OSError, sqlite3.Error) as e:
            logger.error("Failed to create backup: %s", e)
            raise BackupError(f"Failed to create backup: {e}") from e

    def list_backups(self) -> list[BackupInfo]:
        """List all backup files, sorted by creation time (newest first).

        Returns:
            List of BackupInfo objects.

        """
        if not self.backup_dir.exists():
            return []

        backups = []
        for path in self.backup_dir.glob("tools_*.db"):
            if BACKUP_FILENAME_PATTERN.match(path.name):
                try:
                    stat = path.stat()
                    backups.append(
                        BackupInfo(
                            filename=path.name,
                            filepath=path,
                            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                            size_bytes=stat.st_size,
                        )
                    )
                except OSError:
                    continue

        # Sort by creation time, newest first
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups

    def restore_backup(self, filename: str) -> bool:
        """Restore the database from a backup.

        Args:
            filename: Name of the backup file to restore.

        Returns:
            True if restoration was successful.

        Raises:
            InvalidFilenameError: If the filename is invalid.
            BackupNotFoundError: If the backup file doesn't exist.
            BackupError: If the restoration fails.

        """
        # Validate filename
        self._validate_filename(filename)

        backup_path = self.backup_dir / filename
        if not backup_path.exists():
            raise BackupNotFoundError(f"Backup not found: {filename}")

        # Create a temporary backup of current database before restore
        temp_backup_path = self.db_path.with_suffix(".db.restore_backup")
        try:
            # Backup current database using SQLite backup API
            if self.db_path.exists():
                with sqlite3.connect(str(self.db_path)) as src:
                    with sqlite3.connect(str(temp_backup_path)) as dst:
                        src.backup(dst)

            # Restore from backup using SQLite backup API
            with sqlite3.connect(str(backup_path)) as src:
                with sqlite3.connect(str(self.db_path)) as dst:
                    src.backup(dst)
            logger.info("Restored database from backup: %s", filename)

            # Remove temporary backup on success
            if temp_backup_path.exists():
                temp_backup_path.unlink()

            return True
        except (OSError, sqlite3.Error) as e:
            # Attempt to restore from temporary backup on failure
            logger.error("Failed to restore backup: %s", e)
            if temp_backup_path.exists():
                try:
                    with sqlite3.connect(str(temp_backup_path)) as src:
                        with sqlite3.connect(str(self.db_path)) as dst:
                            src.backup(dst)
                    temp_backup_path.unlink()
                    logger.info("Successfully rolled back to previous database state")
                except (OSError, sqlite3.Error) as rollback_error:
                    logger.critical(
                        "CRITICAL: Failed to rollback database after restore failure. "
                        "Database may be in inconsistent state. Error: %s",
                        rollback_error,
                    )
            raise BackupError(f"Failed to restore backup: {e}") from e

    def delete_backup(self, filename: str) -> bool:
        """Delete a backup file.

        Args:
            filename: Name of the backup file to delete.

        Returns:
            True if deletion was successful.

        Raises:
            InvalidFilenameError: If the filename is invalid.
            BackupNotFoundError: If the backup file doesn't exist.

        """
        # Validate filename
        self._validate_filename(filename)

        backup_path = self.backup_dir / filename
        if not backup_path.exists():
            raise BackupNotFoundError(f"Backup not found: {filename}")

        try:
            backup_path.unlink()
            logger.info("Deleted backup: %s", filename)
            return True
        except OSError as e:
            logger.error("Failed to delete backup: %s", e)
            raise BackupError(f"Failed to delete backup: {e}") from e

    def _rotate_backups(self) -> None:
        """Remove old backups exceeding max_generations."""
        backups = self.list_backups()
        if len(backups) > self.max_generations:
            for backup in backups[self.max_generations :]:
                try:
                    backup.filepath.unlink()
                    logger.info("Rotated old backup: %s", backup.filename)
                except OSError as e:
                    logger.warning("Failed to rotate backup %s: %s", backup.filename, e)

    def _validate_filename(self, filename: str) -> None:
        """Validate backup filename for security.

        Args:
            filename: Filename to validate.

        Raises:
            InvalidFilenameError: If the filename is invalid or potentially malicious.

        """
        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            raise InvalidFilenameError("Invalid filename: path traversal not allowed")

        # Check filename pattern
        if not BACKUP_FILENAME_PATTERN.match(filename):
            raise InvalidFilenameError("Invalid filename: must match tools_YYYYMMDD_HHMMSS.db pattern")
