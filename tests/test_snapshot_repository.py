"""Tests for SnapshotRepository."""

import pytest
from sqlmodel import Session

from html_tool_manager.models import Tool
from html_tool_manager.models.snapshot import MAX_SNAPSHOTS_PER_TOOL, SnapshotType
from html_tool_manager.repositories import SnapshotRepository, ToolRepository


@pytest.fixture
def tool(session: Session) -> Tool:
    """Create a test tool."""
    tool_repo = ToolRepository(session)
    tool = Tool(
        name="Test Tool",
        description="Test Description",
        tags=["test"],
        filepath="static/tools/test/index.html",
    )
    return tool_repo.create_tool(tool)


class TestSnapshotRepository:
    """Tests for SnapshotRepository."""

    def test_create_snapshot(self, session: Session, tool: Tool):
        """Test creating a snapshot."""
        repo = SnapshotRepository(session)
        snapshot = repo.create_snapshot(
            tool_id=tool.id,
            html_content="<html>test</html>",
            snapshot_type=SnapshotType.AUTO,
        )

        assert snapshot.id is not None
        assert snapshot.tool_id == tool.id
        assert snapshot.html_content == "<html>test</html>"
        assert snapshot.snapshot_type == SnapshotType.AUTO
        assert snapshot.name is None

    def test_create_manual_snapshot_with_name(self, session: Session, tool: Tool):
        """Test creating a manual snapshot with a name."""
        repo = SnapshotRepository(session)
        snapshot = repo.create_snapshot(
            tool_id=tool.id,
            html_content="<html>test</html>",
            snapshot_type=SnapshotType.MANUAL,
            name="My Snapshot",
        )

        assert snapshot.snapshot_type == SnapshotType.MANUAL
        assert snapshot.name == "My Snapshot"

    def test_get_snapshots_by_tool(self, session: Session, tool: Tool):
        """Test getting snapshots by tool ID."""
        repo = SnapshotRepository(session)

        # Create multiple snapshots
        for i in range(3):
            repo.create_snapshot(
                tool_id=tool.id,
                html_content=f"<html>version {i}</html>",
            )

        snapshots = repo.get_snapshots_by_tool(tool.id)

        assert len(snapshots) == 3
        # Should be ordered by created_at DESC (newest first)
        assert "version 2" in snapshots[0].html_content
        assert "version 0" in snapshots[2].html_content

    def test_get_snapshot(self, session: Session, tool: Tool):
        """Test getting a single snapshot."""
        repo = SnapshotRepository(session)
        created = repo.create_snapshot(
            tool_id=tool.id,
            html_content="<html>test</html>",
        )

        snapshot = repo.get_snapshot(tool.id, created.id)

        assert snapshot is not None
        assert snapshot.id == created.id
        assert snapshot.html_content == "<html>test</html>"

    def test_get_snapshot_wrong_tool_id(self, session: Session, tool: Tool):
        """Test that getting a snapshot with wrong tool_id returns None."""
        repo = SnapshotRepository(session)
        created = repo.create_snapshot(
            tool_id=tool.id,
            html_content="<html>test</html>",
        )

        # Try to get with wrong tool_id
        snapshot = repo.get_snapshot(tool.id + 999, created.id)

        assert snapshot is None

    def test_delete_snapshot(self, session: Session, tool: Tool):
        """Test deleting a snapshot."""
        repo = SnapshotRepository(session)
        created = repo.create_snapshot(
            tool_id=tool.id,
            html_content="<html>test</html>",
        )

        deleted = repo.delete_snapshot(tool.id, created.id)

        assert deleted is not None
        assert deleted.id == created.id

        # Verify it's gone
        assert repo.get_snapshot(tool.id, created.id) is None

    def test_delete_all_by_tool(self, session: Session, tool: Tool):
        """Test deleting all snapshots for a tool."""
        repo = SnapshotRepository(session)

        # Create multiple snapshots
        for i in range(5):
            repo.create_snapshot(
                tool_id=tool.id,
                html_content=f"<html>version {i}</html>",
            )

        count = repo.delete_all_by_tool(tool.id)

        assert count == 5
        assert len(repo.get_snapshots_by_tool(tool.id)) == 0

    def test_retention_limit(self, session: Session, tool: Tool):
        """Test that old snapshots are deleted when exceeding MAX_SNAPSHOTS_PER_TOOL."""
        repo = SnapshotRepository(session)

        # Create more than MAX_SNAPSHOTS_PER_TOOL snapshots
        for i in range(MAX_SNAPSHOTS_PER_TOOL + 5):
            repo.create_snapshot(
                tool_id=tool.id,
                html_content=f"<html>version {i}</html>",
            )

        snapshots = repo.get_snapshots_by_tool(tool.id)

        # Should only have MAX_SNAPSHOTS_PER_TOOL snapshots
        assert len(snapshots) == MAX_SNAPSHOTS_PER_TOOL

        # The oldest snapshots should be deleted (versions 0-4)
        # The newest should remain (versions 5-24)
        contents = [s.html_content for s in snapshots]
        assert "version 0" not in " ".join(contents)
        assert "version 4" not in " ".join(contents)
        assert f"version {MAX_SNAPSHOTS_PER_TOOL + 4}" in " ".join(contents)

    def test_count_snapshots(self, session: Session, tool: Tool):
        """Test counting snapshots."""
        repo = SnapshotRepository(session)

        assert repo.count_snapshots(tool.id) == 0

        for i in range(3):
            repo.create_snapshot(
                tool_id=tool.id,
                html_content=f"<html>version {i}</html>",
            )

        assert repo.count_snapshots(tool.id) == 3
