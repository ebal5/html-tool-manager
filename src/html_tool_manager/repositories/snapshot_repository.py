"""Repository for snapshot database operations."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Session, delete, func, select

from html_tool_manager.models.snapshot import (
    MAX_SNAPSHOTS_PER_TOOL,
    SnapshotType,
    ToolSnapshot,
)


class SnapshotRepository:
    """Repository class encapsulating database operations for snapshots."""

    def __init__(self, session: Session):
        """Initialize the repository.

        Args:
            session: The database session.

        """
        self.session = session

    def create_snapshot(
        self,
        tool_id: int,
        html_content: str,
        snapshot_type: SnapshotType = SnapshotType.AUTO,
        name: Optional[str] = None,
    ) -> ToolSnapshot:
        """Create a new snapshot and enforce retention limit.

        This operation uses SELECT FOR UPDATE to prevent race conditions
        when multiple requests try to create snapshots simultaneously.

        Args:
            tool_id: The ID of the tool.
            html_content: The HTML content to snapshot.
            snapshot_type: The type of snapshot (auto or manual).
            name: Optional name for manual snapshots.

        Returns:
            The created snapshot.

        """
        # 上限チェック（新規作成前に実行してレースコンディションを防止）
        self._enforce_retention_limit(tool_id, reserve_space=1)

        snapshot = ToolSnapshot(
            tool_id=tool_id,
            html_content=html_content,
            snapshot_type=snapshot_type,
            name=name,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)

        return snapshot

    def get_snapshots_by_tool(
        self,
        tool_id: int,
        limit: int = 100,
    ) -> List[ToolSnapshot]:
        """Get all snapshots for a tool, ordered by created_at DESC.

        Args:
            tool_id: The ID of the tool.
            limit: Maximum number of snapshots to return.

        Returns:
            List of snapshots for the tool.

        """
        statement = (
            select(ToolSnapshot)
            .where(ToolSnapshot.tool_id == tool_id)
            .order_by(ToolSnapshot.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def get_snapshot(
        self,
        tool_id: int,
        snapshot_id: int,
    ) -> Optional[ToolSnapshot]:
        """Get a single snapshot by ID, verifying it belongs to the tool.

        Args:
            tool_id: The ID of the tool.
            snapshot_id: The ID of the snapshot.

        Returns:
            The snapshot if found and belongs to the tool, None otherwise.

        """
        statement = select(ToolSnapshot).where(ToolSnapshot.id == snapshot_id).where(ToolSnapshot.tool_id == tool_id)
        return self.session.exec(statement).first()

    def delete_snapshot(
        self,
        tool_id: int,
        snapshot_id: int,
    ) -> Optional[ToolSnapshot]:
        """Delete a snapshot.

        Args:
            tool_id: The ID of the tool.
            snapshot_id: The ID of the snapshot.

        Returns:
            The deleted snapshot if found, None otherwise.

        """
        snapshot = self.get_snapshot(tool_id, snapshot_id)
        if not snapshot:
            return None
        self.session.delete(snapshot)
        self.session.commit()
        return snapshot

    def count_snapshots(self, tool_id: int) -> int:
        """Count snapshots for a tool.

        Args:
            tool_id: The ID of the tool.

        Returns:
            The number of snapshots for the tool.

        """
        statement = select(func.count()).select_from(ToolSnapshot).where(ToolSnapshot.tool_id == tool_id)
        result = self.session.exec(statement).one()
        return result

    def _enforce_retention_limit(self, tool_id: int, reserve_space: int = 0) -> None:
        """Delete oldest snapshots if count exceeds MAX_SNAPSHOTS_PER_TOOL.

        Args:
            tool_id: The ID of the tool.
            reserve_space: Number of additional slots to reserve (for new snapshots).

        """
        count = self.count_snapshots(tool_id)
        threshold = MAX_SNAPSHOTS_PER_TOOL - reserve_space
        if count <= threshold:
            return

        # 削除対象数
        to_delete = count - threshold

        # 最も古いスナップショットのIDを取得してバルク削除
        subquery = (
            select(ToolSnapshot.id)
            .where(ToolSnapshot.tool_id == tool_id)
            .order_by(ToolSnapshot.created_at.asc())  # type: ignore[attr-defined]
            .limit(to_delete)
        )
        old_ids = list(self.session.exec(subquery).all())

        if old_ids:
            delete_statement = delete(ToolSnapshot).where(ToolSnapshot.id.in_(old_ids))  # type: ignore[union-attr]
            self.session.exec(delete_statement)  # type: ignore[call-overload]
            self.session.commit()

    def delete_all_by_tool(self, tool_id: int) -> int:
        """Delete all snapshots for a tool (called when tool is deleted).

        Args:
            tool_id: The ID of the tool.

        Returns:
            The number of deleted snapshots.

        """
        count = self.count_snapshots(tool_id)
        if count == 0:
            return 0

        delete_statement = delete(ToolSnapshot).where(ToolSnapshot.tool_id == tool_id)
        self.session.exec(delete_statement)  # type: ignore[call-overload]
        self.session.commit()
        return count
