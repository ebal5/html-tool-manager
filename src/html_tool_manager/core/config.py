"""Application configuration settings."""

import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Core application settings.

    All settings can be overridden via environment variables.
    """

    database_path: str = "./tools.db"
    tools_dir: str = "static/tools"

    model_config = {"env_prefix": "APP_"}

    @field_validator("tools_dir")
    @classmethod
    def validate_tools_dir(cls, v: str) -> str:
        """Validate tools_dir path for security.

        Args:
            v: The tools_dir path to validate

        Returns:
            The validated path

        Raises:
            ValueError: If the path is invalid or dangerous
        """
        if not v:
            raise ValueError("tools_dir cannot be empty")

        # Normalize path to resolve any . or .. components
        normalized = os.path.normpath(v)

        # Check for path traversal attempts
        if ".." in Path(normalized).parts:
            raise ValueError("Path traversal (..) is not allowed in tools_dir")

        # Define dangerous system paths
        dangerous_prefixes = [
            "/etc",
            "/usr",
            "/sys",
            "/proc",
            "/boot",
            "/dev",
            "/root",
        ]

        # For absolute paths, check against dangerous prefixes
        if os.path.isabs(normalized):
            for prefix in dangerous_prefixes:
                if normalized.startswith(prefix):
                    raise ValueError(
                        f"tools_dir cannot be set to system directory: {prefix}"
                    )

        return v


class BackupSettings(BaseSettings):
    """Settings for database backup functionality.

    All settings can be overridden via environment variables with BACKUP_ prefix.
    """

    backup_dir: str = "backups"
    backup_interval_hours: int = 24
    backup_max_generations: int = 7
    backup_on_startup: bool = True

    model_config = {"env_prefix": "BACKUP_"}


app_settings = AppSettings()
backup_settings = BackupSettings()
