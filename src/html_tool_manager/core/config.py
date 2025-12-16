"""Application configuration settings."""

from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Core application settings.

    All settings can be overridden via environment variables.
    """

    database_path: str = "./tools.db"
    tools_dir: str = "static/tools"

    model_config = {"env_prefix": "APP_"}


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
