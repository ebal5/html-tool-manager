"""File utilities for safe file operations."""

import os
import tempfile


def atomic_write_file(filepath: str, content: str, mode: int = 0o644) -> None:
    """Write content to a file atomically.

    Uses a temporary file and os.replace() to ensure atomic writes.
    This prevents file corruption if the process crashes during write.

    Args:
        filepath: The target file path to write to.
        content: The content to write.
        mode: File permission mode (default: 0o644).

    Raises:
        OSError: If file operations fail.
        PermissionError: If permission is denied.

    """
    dir_path = os.path.dirname(filepath)

    # Create temp file in the same directory for atomic replace
    temp_fd, temp_path = tempfile.mkstemp(dir=dir_path, text=True)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        # Set permissions before replace
        os.chmod(temp_path, mode)
        # Atomic replace (works on POSIX and Windows)
        os.replace(temp_path, filepath)
    except BaseException:
        # Clean up temp file on any error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
