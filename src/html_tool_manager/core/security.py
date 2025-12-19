"""Security utilities for path validation."""

import os


def is_path_within_base(target_path: str, base_path: str) -> bool:
    r"""Check if target_path is safely within base_path.

    Uses os.path.commonpath() for cross-platform path traversal detection.
    This is more robust than startswith() checks, especially on Windows
    where both '/' and '\\' are valid path separators.

    Args:
        target_path: The path to validate (will be resolved to real path).
        base_path: The base directory that target_path must be within.

    Returns:
        True if target_path is within base_path, False otherwise.

    Note:
        - Both paths are resolved to their real paths (resolving symlinks)
        - Returns False if paths are on different drives (Windows)
        - Returns False for empty paths or on path resolution failure

    """
    if not target_path or not base_path:
        return False

    try:
        real_target = os.path.realpath(target_path)
        real_base = os.path.realpath(base_path)
        common = os.path.commonpath([real_target, real_base])
        return common == real_base
    except (ValueError, OSError):
        # ValueError: different drives on Windows, or empty path list
        # OSError: path resolution failure
        return False
