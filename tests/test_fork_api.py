"""Tests for Fork API endpoint."""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from html_tool_manager.models import Tool
from html_tool_manager.models.tool import NAME_MAX_LENGTH, ToolType
from html_tool_manager.repositories import ToolRepository


@pytest.fixture
def tool_with_file(session: Session, test_tools_dir: Path) -> Tool:
    """Create a test tool with an actual file in the test directory."""
    tool_dir = test_tools_dir / f"test-{uuid.uuid4()}"
    tool_dir.mkdir()
    filepath = tool_dir / "index.html"

    filepath.write_text("<html><body>Original content</body></html>", encoding="utf-8")

    tool_repo = ToolRepository(session)
    tool = Tool(
        name="Original Tool",
        description="Original Description",
        tags=["original", "test"],
        filepath=str(filepath),
        tool_type=ToolType.HTML,
    )
    return tool_repo.create_tool(tool)


@pytest.fixture
def react_tool_with_file(session: Session, test_tools_dir: Path) -> Tool:
    """Create a React type test tool with an actual file."""
    tool_dir = test_tools_dir / f"react-{uuid.uuid4()}"
    tool_dir.mkdir()
    filepath = tool_dir / "index.html"

    react_content = """<!DOCTYPE html>
<html>
<head><script src="https://unpkg.com/react.production.min.js"></script></head>
<body><div id="root"></div></body>
</html>"""
    filepath.write_text(react_content, encoding="utf-8")

    tool_repo = ToolRepository(session)
    tool = Tool(
        name="React Tool",
        description="React Description",
        tags=["react", "test"],
        filepath=str(filepath),
        tool_type=ToolType.REACT,
    )
    return tool_repo.create_tool(tool)


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

    def test_fork_nonexistent_tool(self, client: TestClient, session: Session, test_tools_dir: Path):
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
        forked_content = Path(forked_tool["filepath"]).read_text(encoding="utf-8")

        # Read original content
        original_content = Path(tool_with_file.filepath).read_text(encoding="utf-8")

        assert forked_content == original_content

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

    def test_fork_long_name_truncation(self, client: TestClient, session: Session, test_tools_dir: Path):
        """Test forking a tool with very long name truncates appropriately."""
        tool_dir = test_tools_dir / f"long-name-{uuid.uuid4()}"
        tool_dir.mkdir()
        filepath = tool_dir / "index.html"
        filepath.write_text("<html><body>Content</body></html>", encoding="utf-8")

        tool_repo = ToolRepository(session)
        # Create a tool with name at max length
        long_name = "A" * NAME_MAX_LENGTH
        tool = Tool(
            name=long_name,
            description="Test",
            tags=[],
            filepath=str(filepath),
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

    def test_fork_react_tool_preserves_type(self, client: TestClient, react_tool_with_file: Tool):
        """Test forking a React tool preserves the tool_type."""
        response = client.post(
            f"/api/tools/{react_tool_with_file.id}/fork",
            json={"name": "Forked React Tool"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tool_type"] == "react"
        assert data["name"] == "Forked React Tool"

    def test_fork_with_special_characters_in_name(self, client: TestClient, tool_with_file: Tool):
        """Test forking with special characters in name."""
        special_name = 'ツール <Test> & "Fork"'
        response = client.post(
            f"/api/tools/{tool_with_file.id}/fork",
            json={"name": special_name},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == special_name

    def test_fork_tool_with_no_description(self, client: TestClient, session: Session, test_tools_dir: Path):
        """Test forking a tool that has no description."""
        tool_dir = test_tools_dir / f"no-desc-{uuid.uuid4()}"
        tool_dir.mkdir()
        filepath = tool_dir / "index.html"
        filepath.write_text("<html><body>No desc</body></html>", encoding="utf-8")

        tool_repo = ToolRepository(session)
        tool = Tool(
            name="No Description Tool",
            description=None,
            tags=[],
            filepath=str(filepath),
        )
        created_tool = tool_repo.create_tool(tool)

        response = client.post(
            f"/api/tools/{created_tool.id}/fork",
            json={"name": "Forked No Desc"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["description"] is None

    def test_fork_tool_file_not_found(self, client: TestClient, session: Session, test_tools_dir: Path):
        """Test forking when the tool file has been deleted."""
        tool_dir = test_tools_dir / f"deleted-{uuid.uuid4()}"
        tool_dir.mkdir()
        filepath = tool_dir / "index.html"
        filepath.write_text("<html><body>Will be deleted</body></html>", encoding="utf-8")

        tool_repo = ToolRepository(session)
        tool = Tool(
            name="Deleted File Tool",
            description="Test",
            tags=[],
            filepath=str(filepath),
        )
        created_tool = tool_repo.create_tool(tool)

        # Delete the file after creating the DB record
        filepath.unlink()

        response = client.post(
            f"/api/tools/{created_tool.id}/fork",
            json={"name": "Fork Deleted"},
        )

        assert response.status_code == 404
        assert "Tool file not found" in response.json()["detail"]
