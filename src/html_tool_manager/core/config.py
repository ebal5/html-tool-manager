"""Backup configuration settings."""

from pydantic_settings import BaseSettings


class BackupSettings(BaseSettings):
    """Settings for database backup functionality.

    All settings can be overridden via environment variables with BACKUP_ prefix.
    """

    backup_dir: str = "backups"
    backup_interval_hours: int = 24
    backup_max_generations: int = 7
    backup_on_startup: bool = True

    model_config = {"env_prefix": "BACKUP_"}


backup_settings = BackupSettings()
