"""Tests for Snapshot API endpoints."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from html_tool_manager.models import Tool
from html_tool_manager.repositories import SnapshotRepository, ToolRepository


@pytest.fixture
def tool_with_file(session: Session) -> Tool:
    """Create a test tool with an actual file."""
    # Ensure static/tools directory exists
    os.makedirs("static/tools", exist_ok=True)

    # Create a temporary directory for the tool with a unique name
    import uuid

    tool_dir = f"static/tools/test-{uuid.uuid4()}"
    os.makedirs(tool_dir, exist_ok=True)
    filepath = os.path.join(tool_dir, "index.html")

    # Write initial content
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("<html><body>Initial content</body></html>")

    tool_repo = ToolRepository(session)
    tool = Tool(
        name="Test Tool",
        description="Test Description",
        tags=["test"],
        filepath=filepath,
    )
    created_tool = tool_repo.create_tool(tool)

    yield created_tool

    # Cleanup
    try:
        os.remove(filepath)
        os.rmdir(tool_dir)
    except OSError:
        pass


class TestSnapshotAPI:
    """Tests for Snapshot API endpoints."""

    def test_list_snapshots_empty(self, client: TestClient, tool_with_file: Tool):
        """Test listing snapshots when none exist."""
        response = client.get(f"/api/tools/{tool_with_file.id}/snapshots")

        assert response.status_code == 200
        assert response.json() == []

    def test_create_manual_snapshot(self, client: TestClient, tool_with_file: Tool):
        """Test creating a manual snapshot."""
        response = client.post(
            f"/api/tools/{tool_with_file.id}/snapshots",
            json={"name": "My Snapshot", "snapshot_type": "manual"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Snapshot"
        assert data["snapshot_type"] == "manual"
        assert data["tool_id"] == tool_with_file.id

    def test_list_snapshots_after_creation(self, client: TestClient, tool_with_file: Tool):
        """Test listing snapshots after creating some."""
        # Create snapshots
        client.post(
            f"/api/tools/{tool_with_file.id}/snapshots",
            json={"name": "Snapshot 1", "snapshot_type": "manual"},
        )
        client.post(
            f"/api/tools/{tool_with_file.id}/snapshots",
            json={"name": "Snapshot 2", "snapshot_type": "manual"},
        )

        response = client.get(f"/api/tools/{tool_with_file.id}/snapshots")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Should be ordered by created_at DESC (newest first)
        assert data[0]["name"] == "Snapshot 2"
        assert data[1]["name"] == "Snapshot 1"

    def test_get_snapshot_with_content(self, client: TestClient, tool_with_file: Tool):
        """Test getting a single snapshot with its content."""
        # Create a snapshot
        create_response = client.post(
            f"/api/tools/{tool_with_file.id}/snapshots",
            json={"name": "Test Snapshot", "snapshot_type": "manual"},
        )
        snapshot_id = create_response.json()["id"]

        response = client.get(f"/api/tools/{tool_with_file.id}/snapshots/{snapshot_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == snapshot_id
        assert data["name"] == "Test Snapshot"
        assert "html_content" in data
        assert "Initial content" in data["html_content"]

    def test_get_snapshot_not_found(self, client: TestClient, tool_with_file: Tool):
        """Test getting a non-existent snapshot."""
        response = client.get(f"/api/tools/{tool_with_file.id}/snapshots/99999")

        assert response.status_code == 404

    def test_delete_snapshot(self, client: TestClient, tool_with_file: Tool):
        """Test deleting a snapshot."""
        # Create a snapshot
        create_response = client.post(
            f"/api/tools/{tool_with_file.id}/snapshots",
            json={"name": "To Delete", "snapshot_type": "manual"},
        )
        snapshot_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/tools/{tool_with_file.id}/snapshots/{snapshot_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/tools/{tool_with_file.id}/snapshots/{snapshot_id}")
        assert get_response.status_code == 404

    def test_restore_snapshot(self, client: TestClient, tool_with_file: Tool):
        """Test restoring a snapshot."""
        # Create a snapshot
        create_response = client.post(
            f"/api/tools/{tool_with_file.id}/snapshots",
            json={"name": "Original State", "snapshot_type": "manual"},
        )
        snapshot_id = create_response.json()["id"]

        # Modify the file
        with open(tool_with_file.filepath, "w", encoding="utf-8") as f:
            f.write("<html><body>Modified content</body></html>")

        # Restore
        response = client.post(f"/api/tools/{tool_with_file.id}/snapshots/{snapshot_id}/restore")

        assert response.status_code == 200

        # Verify file content is restored
        with open(tool_with_file.filepath, encoding="utf-8") as f:
            content = f.read()
        assert "Initial content" in content

    def test_get_diff(self, client: TestClient, tool_with_file: Tool, session: Session):
        """Test getting diff between snapshot and current content."""
        # Create a snapshot
        create_response = client.post(
            f"/api/tools/{tool_with_file.id}/snapshots",
            json={"name": "Snapshot", "snapshot_type": "manual"},
        )
        snapshot_id = create_response.json()["id"]

        # Modify the file
        with open(tool_with_file.filepath, "w", encoding="utf-8") as f:
            f.write("<html><body>New content</body></html>")

        response = client.get(f"/api/tools/{tool_with_file.id}/snapshots/{snapshot_id}/diff")

        assert response.status_code == 200
        data = response.json()
        assert data["old_snapshot_id"] == snapshot_id
        assert "Initial content" in data["old_content"]
        assert "New content" in data["new_content"]
        assert data["new_snapshot_id"] is None  # Comparing to current

    def test_tool_not_found(self, client: TestClient):
        """Test that snapshot endpoints return 404 for non-existent tool."""
        response = client.get("/api/tools/99999/snapshots")
        assert response.status_code == 404

    def test_auto_snapshot_on_update(self, client: TestClient, tool_with_file: Tool, session: Session):
        """Test that updating tool content creates an automatic snapshot."""
        # Update the tool content
        response = client.put(
            f"/api/tools/{tool_with_file.id}",
            json={
                "name": tool_with_file.name,
                "description": tool_with_file.description,
                "tags": tool_with_file.tags,
                "filepath": tool_with_file.filepath,
                "html_content": "<html><body>Updated content</body></html>",
            },
        )

        assert response.status_code == 200

        # Check that a snapshot was created
        snapshots_response = client.get(f"/api/tools/{tool_with_file.id}/snapshots")
        snapshots = snapshots_response.json()

        assert len(snapshots) == 1
        assert snapshots[0]["snapshot_type"] == "auto"

    def test_no_snapshot_on_same_content(self, client: TestClient, tool_with_file: Tool):
        """Test that no snapshot is created when content is unchanged."""
        # Read current content
        with open(tool_with_file.filepath, encoding="utf-8") as f:
            current_content = f.read()

        # Update with same content
        response = client.put(
            f"/api/tools/{tool_with_file.id}",
            json={
                "name": tool_with_file.name,
                "description": tool_with_file.description,
                "tags": tool_with_file.tags,
                "filepath": tool_with_file.filepath,
                "html_content": current_content,
            },
        )

        assert response.status_code == 200

        # Check that no snapshot was created
        snapshots_response = client.get(f"/api/tools/{tool_with_file.id}/snapshots")
        snapshots = snapshots_response.json()

        assert len(snapshots) == 0

    def test_delete_tool_deletes_snapshots(self, client: TestClient, tool_with_file: Tool, session: Session):
        """Test that deleting a tool also deletes its snapshots."""
        # Create some snapshots
        for i in range(3):
            client.post(
                f"/api/tools/{tool_with_file.id}/snapshots",
                json={"name": f"Snapshot {i}", "snapshot_type": "manual"},
            )

        # Verify snapshots exist
        repo = SnapshotRepository(session)
        assert repo.count_snapshots(tool_with_file.id) == 3

        # Delete the tool
        response = client.delete(f"/api/tools/{tool_with_file.id}")
        assert response.status_code == 204

        # Verify snapshots are also deleted
        assert repo.count_snapshots(tool_with_file.id) == 0
