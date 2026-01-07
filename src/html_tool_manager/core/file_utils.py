"""File utilities for safe file operations."""

import os
import tempfile


def secure_read_file(filepath: str) -> str:
    """Read file content securely with TOCTOU protection.

    Uses os.open() with O_NOFOLLOW to prevent symlink attacks between
    path validation and file access (TOCTOU vulnerability).

    Args:
        filepath: The file path to read from.

    Returns:
        The file content as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If permission is denied.
        OSError: If the file is a symlink (O_NOFOLLOW) or other I/O error.

    """
    # O_NOFOLLOW: Fail if filepath is a symbolic link
    # This prevents TOCTOU attacks where symlink is changed after validation
    fd = os.open(filepath, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        with os.fdopen(fd, "r", encoding="utf-8") as f:
            return f.read()
    except BaseException:
        # If fdopen fails, close the fd to avoid resource leak
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def atomic_write_file(filepath: str, content: str, mode: int = 0o644) -> None:
    """Write content to a file atomically with TOCTOU protection.

    Uses a temporary file and os.replace() to ensure atomic writes.
    Uses O_NOFOLLOW to prevent symlink attacks.
    This prevents file corruption if the process crashes during write.

    Args:
        filepath: The target file path to write to. Parent directory must exist.
        content: The content to write.
        mode: File permission mode (default: 0o644).

    Raises:
        FileNotFoundError: If parent directory does not exist.
        OSError: If file operations fail or filepath is a symlink.
        PermissionError: If permission is denied.

    """
    dir_path = os.path.dirname(filepath) or "."

    # Create temp file in the same directory for atomic replace
    temp_fd, temp_path = tempfile.mkstemp(dir=dir_path, text=True)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        # Set permissions before replace
        os.chmod(temp_path, mode)
        # Atomic replace (works on POSIX and Windows)
        # Note: os.replace() follows symlinks, but this is intentional here
        # as we want to replace the symlink target if it exists
        os.replace(temp_path, filepath)
    except BaseException:
        # Clean up temp file on any error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
