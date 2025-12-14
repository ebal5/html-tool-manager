"""API endpoints for backup operations."""

from fastapi import APIRouter, HTTPException, Request, status

from html_tool_manager.core.backup import (
    BackupError,
    BackupNotFoundError,
    BackupService,
    InvalidFilenameError,
)
from html_tool_manager.models.backup import (
    BackupCreateResponse,
    BackupInfoResponse,
    BackupListResponse,
    BackupRestoreResponse,
)

router = APIRouter(prefix="/backup", tags=["backup"])


def _get_backup_service(request: Request) -> BackupService:
    """Get BackupService from app state."""
    return request.app.state.backup_service


def _backup_to_response(backup_info: "BackupService") -> BackupInfoResponse:
    """Convert BackupInfo to BackupInfoResponse."""
    from html_tool_manager.core.backup import BackupInfo

    if not isinstance(backup_info, BackupInfo):
        raise TypeError("Expected BackupInfo instance")
    return BackupInfoResponse(
        filename=backup_info.filename,
        created_at=backup_info.created_at,
        size_bytes=backup_info.size_bytes,
        size_human=backup_info.size_human,
    )


@router.get("/", response_model=BackupListResponse)
def list_backups(request: Request) -> BackupListResponse:
    """List all backup files.

    Returns:
        List of backup files sorted by creation date (newest first).

    """
    service = _get_backup_service(request)
    backups = service.list_backups()
    return BackupListResponse(
        backups=[_backup_to_response(b) for b in backups],
        total_count=len(backups),
    )


@router.post("/", response_model=BackupCreateResponse, status_code=status.HTTP_201_CREATED)
def create_backup(request: Request) -> BackupCreateResponse:
    """Create a manual backup.

    Returns:
        Information about the created backup.

    """
    service = _get_backup_service(request)
    try:
        backup = service.create_backup()
        return BackupCreateResponse(
            success=True,
            backup=_backup_to_response(backup),
            message="Backup created successfully",
        )
    except BackupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.post("/restore/{filename}", response_model=BackupRestoreResponse)
def restore_backup(request: Request, filename: str) -> BackupRestoreResponse:
    """Restore the database from a backup.

    Args:
        request: FastAPI request object for accessing app state.
        filename: Name of the backup file to restore from.

    Returns:
        Information about the restoration.

    Note:
        After restoration, the application may need to be restarted
        to reflect the changes properly.

    """
    service = _get_backup_service(request)
    try:
        service.restore_backup(filename)
        return BackupRestoreResponse(
            success=True,
            message="Database restored successfully. Application restart may be required.",
            restored_from=filename,
        )
    except InvalidFilenameError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except BackupNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except BackupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backup(request: Request, filename: str) -> None:
    """Delete a backup file.

    Args:
        request: FastAPI request object for accessing app state.
        filename: Name of the backup file to delete.

    """
    service = _get_backup_service(request)
    try:
        service.delete_backup(filename)
    except InvalidFilenameError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except BackupNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except BackupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
