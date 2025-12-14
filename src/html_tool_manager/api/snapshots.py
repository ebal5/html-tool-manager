"""Snapshot API endpoints."""

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

from html_tool_manager.core.db import get_session
from html_tool_manager.models import (
    SnapshotCreate,
    SnapshotRead,
    SnapshotReadWithContent,
    SnapshotType,
    ToolRead,
)
from html_tool_manager.models.tool import ToolType
from html_tool_manager.repositories import SnapshotRepository, ToolRepository
from html_tool_manager.templates.react_template import generate_react_html

router = APIRouter(prefix="/tools/{tool_id}/snapshots", tags=["snapshots"])


class DiffResponse(BaseModel):
    """Response model for diff endpoint."""

    old_snapshot_id: int
    old_content: str
    new_snapshot_id: Optional[int]  # None = current content
    new_content: str


def _get_tool_or_404(tool_id: int, session: Session) -> None:
    """Verify that the tool exists, raise 404 if not."""
    repo = ToolRepository(session)
    tool = repo.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")


def _read_current_content(filepath: str) -> str:
    """Read current HTML content from file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool file not found")
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Permission denied when reading file",
        )
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {e}",
        )


@router.get("/", response_model=List[SnapshotRead])
def list_snapshots(
    tool_id: int,
    session: Session = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=100, description="取得件数（1-100）"),
) -> List[SnapshotRead]:
    """Get a list of snapshots for a tool."""
    _get_tool_or_404(tool_id, session)

    snapshot_repo = SnapshotRepository(session)
    snapshots = snapshot_repo.get_snapshots_by_tool(tool_id, limit=limit)

    return [SnapshotRead.model_validate(s) for s in snapshots]


@router.post("/", response_model=SnapshotRead, status_code=status.HTTP_201_CREATED)
def create_snapshot(
    tool_id: int,
    snapshot_data: SnapshotCreate,
    session: Session = Depends(get_session),
) -> SnapshotRead:
    """Create a manual snapshot."""
    tool_repo = ToolRepository(session)
    tool = tool_repo.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    # Read current content from file
    current_content = _read_current_content(tool.filepath)

    snapshot_repo = SnapshotRepository(session)
    try:
        snapshot = snapshot_repo.create_snapshot(
            tool_id=tool_id,
            html_content=current_content,
            snapshot_type=snapshot_data.snapshot_type or SnapshotType.MANUAL,
            name=snapshot_data.name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        )

    return SnapshotRead.model_validate(snapshot)


@router.get("/{snapshot_id}", response_model=SnapshotReadWithContent)
def get_snapshot(
    tool_id: int,
    snapshot_id: int,
    session: Session = Depends(get_session),
) -> SnapshotReadWithContent:
    """Get a single snapshot with its content."""
    _get_tool_or_404(tool_id, session)

    snapshot_repo = SnapshotRepository(session)
    snapshot = snapshot_repo.get_snapshot(tool_id, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    return SnapshotReadWithContent.model_validate(snapshot)


@router.delete("/{snapshot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_snapshot(
    tool_id: int,
    snapshot_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Delete a snapshot."""
    _get_tool_or_404(tool_id, session)

    snapshot_repo = SnapshotRepository(session)
    snapshot = snapshot_repo.delete_snapshot(tool_id, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    return None


@router.post("/{snapshot_id}/restore", response_model=ToolRead)
def restore_snapshot(
    tool_id: int,
    snapshot_id: int,
    session: Session = Depends(get_session),
) -> ToolRead:
    """Restore a tool to a previous snapshot.

    This creates a new snapshot of the current content after successful restoration.
    The order ensures atomicity: file write first, then DB commit.
    """
    tool_repo = ToolRepository(session)
    tool = tool_repo.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    snapshot_repo = SnapshotRepository(session)
    snapshot = snapshot_repo.get_snapshot(tool_id, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    # Validate filepath first
    filepath = tool.filepath
    if not filepath or ".." in filepath or not filepath.startswith("static/tools/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filepath")

    # Verify real path
    real_path = os.path.realpath(filepath)
    expected_base = os.path.realpath("static/tools")
    if not real_path.startswith(expected_base + os.sep):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filepath: path traversal detected",
        )

    # Read current content before overwriting (for backup snapshot)
    current_content = _read_current_content(tool.filepath)

    # Prepare content to write - handle React template if needed
    content_to_write = snapshot.html_content
    if tool.tool_type == ToolType.REACT:
        # Check if snapshot content is raw JSX (not wrapped in template)
        # If it doesn't contain the React CDN, it's likely raw JSX
        if "react.production.min.js" not in snapshot.html_content:
            content_to_write = generate_react_html(snapshot.html_content)

    # Write file first - if this fails, no DB changes are made
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content_to_write)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Permission denied when writing file",
        )
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write file: {e}",
        )

    # File write succeeded - now create backup snapshot of the previous content
    try:
        snapshot_repo.create_snapshot(
            tool_id=tool_id,
            html_content=current_content,
            snapshot_type=SnapshotType.AUTO,
            name="復元前の自動保存",
        )
    except ValueError:
        # Content too large for snapshot - restoration succeeded but backup skipped
        pass

    # Refresh tool and return
    session.refresh(tool)
    return ToolRead.model_validate(tool)


@router.get("/{snapshot_id}/diff", response_model=DiffResponse)
def get_diff(
    tool_id: int,
    snapshot_id: int,
    session: Session = Depends(get_session),
    compare_to: Optional[int] = Query(None, description="比較対象のスナップショットID（省略時は現在の内容）"),
) -> DiffResponse:
    """Get diff between a snapshot and current content (or another snapshot)."""
    tool_repo = ToolRepository(session)
    tool = tool_repo.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    snapshot_repo = SnapshotRepository(session)
    snapshot = snapshot_repo.get_snapshot(tool_id, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    old_content = snapshot.html_content

    if compare_to is not None:
        # Compare with another snapshot
        compare_snapshot = snapshot_repo.get_snapshot(tool_id, compare_to)
        if not compare_snapshot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compare snapshot not found")
        new_content = compare_snapshot.html_content
        new_snapshot_id = compare_to
    else:
        # Compare with current content
        new_content = _read_current_content(tool.filepath)
        new_snapshot_id = None

    return DiffResponse(
        old_snapshot_id=snapshot_id,
        old_content=old_content,
        new_snapshot_id=new_snapshot_id,
        new_content=new_content,
    )
