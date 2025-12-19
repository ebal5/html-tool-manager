"""Tests for Fork API endpoint."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from html_tool_manager.models import Tool
from html_tool_manager.models.tool import NAME_MAX_LENGTH
from html_tool_manager.repositories import ToolRepository


@pytest.fixture
def tool_with_file(session: Session) -> Tool:
    """Create a test tool with an actual file."""
    os.makedirs("static/tools", exist_ok=True)
    tool_dir = f"static/tools/test-{uuid.uuid4()}"
    os.makedirs(tool_dir, exist_ok=True)
    filepath = os.path.join(tool_dir, "index.html")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("<html><body>Original content</body></html>")

    tool_repo = ToolRepository(session)
    tool = Tool(
        name="Original Tool",
        description="Original Description",
        tags=["original", "test"],
        filepath=filepath,
        tool_type="html",
    )
    created_tool = tool_repo.create_tool(tool)

    yield created_tool

    # Cleanup
    try:
        os.remove(filepath)
        os.rmdir(tool_dir)
    except OSError:
        pass


class TestForkAPI:
    """Tests for Fork API endpoint."""

    def test_fork_with_custom_name(self, client: TestClient, tool_with_file: Tool):
        """Test forking a tool with a custom name."""
        response = client.post(
            f"/api/tools/{tool_with_file.id}/fork",
            json={"name": "My Forked Tool"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Forked Tool"
        assert data["description"] == tool_with_file.description
        assert data["tags"] == tool_with_file.tags
        assert data["tool_type"] == tool_with_file.tool_type
        assert data["id"] != tool_with_file.id

    def test_fork_with_empty_name(self, client: TestClient, tool_with_file: Tool):
        """Test forking with empty name uses default."""
        response = client.post(
            f"/api/tools/{tool_with_file.id}/fork",
            json={"name": ""},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Original Tool (Fork)"

    def test_fork_with_null_name(self, client: TestClient, tool_with_file: Tool):
        """Test forking with null name uses default."""
        response = client.post(
            f"/api/tools/{tool_with_file.id}/fork",
            json={"name": None},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Original Tool (Fork)"

    def test_fork_without_name_field(self, client: TestClient, tool_with_file: Tool):
        """Test forking without name field uses default."""
        response = client.post(
            f"/api/tools/{tool_with_file.id}/fork",
            json={},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Original Tool (Fork)"

    def test_fork_nonexistent_tool(self, client: TestClient, session: Session):
        """Test forking a non-existent tool returns 404."""
        response = client.post(
            "/api/tools/99999/fork",
            json={"name": "Fork of Nothing"},
        )

        assert response.status_code == 404

    def test_fork_preserves_content(self, client: TestClient, tool_with_file: Tool):
        """Test that forked tool preserves HTML content."""
        response = client.post(
            f"/api/tools/{tool_with_file.id}/fork",
            json={"name": "Content Check"},
        )

        assert response.status_code == 201
        forked_tool = response.json()

        # Read forked content
        with open(forked_tool["filepath"], encoding="utf-8") as f:
            forked_content = f.read()

        # Read original content
        with open(tool_with_file.filepath, encoding="utf-8") as f:
            original_content = f.read()

        assert forked_content == original_content

        # Cleanup forked file
        try:
            os.remove(forked_tool["filepath"])
            os.rmdir(os.path.dirname(forked_tool["filepath"]))
        except OSError:
            pass

    def test_fork_creates_separate_file(self, client: TestClient, tool_with_file: Tool):
        """Test that forked tool has a separate file."""
        response = client.post(
            f"/api/tools/{tool_with_file.id}/fork",
            json={"name": "Separate File"},
        )

        assert response.status_code == 201
        forked_tool = response.json()

        # Filepath should be different
        assert forked_tool["filepath"] != tool_with_file.filepath

        # Cleanup forked file
        try:
            os.remove(forked_tool["filepath"])
            os.rmdir(os.path.dirname(forked_tool["filepath"]))
        except OSError:
            pass

    def test_fork_long_name_truncation(self, client: TestClient, session: Session):
        """Test forking a tool with very long name truncates appropriately."""
        os.makedirs("static/tools", exist_ok=True)
        tool_dir = f"static/tools/test-{uuid.uuid4()}"
        os.makedirs(tool_dir, exist_ok=True)
        filepath = os.path.join(tool_dir, "index.html")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("<html><body>Content</body></html>")

        tool_repo = ToolRepository(session)
        # Create a tool with name at max length
        long_name = "A" * NAME_MAX_LENGTH
        tool = Tool(
            name=long_name,
            description="Test",
            tags=[],
            filepath=filepath,
        )
        created_tool = tool_repo.create_tool(tool)

        response = client.post(
            f"/api/tools/{created_tool.id}/fork",
            json={},  # Use default name
        )

        assert response.status_code == 201
        data = response.json()
        # Name should be truncated + " (Fork)" = max 100 chars
        assert len(data["name"]) <= NAME_MAX_LENGTH
        assert data["name"].endswith(" (Fork)")

        # Cleanup
        try:
            os.remove(data["filepath"])
            os.rmdir(os.path.dirname(data["filepath"]))
            os.remove(filepath)
            os.rmdir(tool_dir)
        except OSError:
            pass

    def test_fork_name_validation_too_long(self, client: TestClient, tool_with_file: Tool):
        """Test that too long custom name returns 400."""
        response = client.post(
            f"/api/tools/{tool_with_file.id}/fork",
            json={"name": "A" * (NAME_MAX_LENGTH + 1)},
        )

        assert response.status_code == 400

    def test_fork_preserves_tags_independently(self, client: TestClient, tool_with_file: Tool):
        """Test that forked tool's tags are independent of original."""
        response = client.post(
            f"/api/tools/{tool_with_file.id}/fork",
            json={"name": "Independent Tags"},
        )

        assert response.status_code == 201
        forked_tool = response.json()

        # Verify tags are equal but independent
        assert forked_tool["tags"] == tool_with_file.tags

        # Cleanup forked file
        try:
            os.remove(forked_tool["filepath"])
            os.rmdir(os.path.dirname(forked_tool["filepath"]))
        except OSError:
            pass
