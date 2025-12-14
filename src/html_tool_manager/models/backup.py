"""Pydantic models for backup API responses."""

from datetime import datetime

from pydantic import BaseModel


class BackupInfoResponse(BaseModel):
    """Response model for backup file information."""

    filename: str
    created_at: datetime
    size_bytes: int
    size_human: str


class BackupListResponse(BaseModel):
    """Response model for backup list."""

    backups: list[BackupInfoResponse]
    total_count: int


class BackupCreateResponse(BaseModel):
    """Response model for backup creation."""

    success: bool
    backup: BackupInfoResponse
    message: str


class BackupRestoreResponse(BaseModel):
    """Response model for backup restoration."""

    success: bool
    message: str
    restored_from: str


class BackupDeleteResponse(BaseModel):
    """Response model for backup deletion."""

    success: bool
    message: str
