"""Tests for the tag suggestion endpoint."""

from fastapi.testclient import TestClient

from html_tool_manager.main import app

client = TestClient(app)


def test_tag_suggest_returns_empty_list_when_no_tools() -> None:
    """Test that tag suggest returns empty list when no tools exist."""
    response = client.get("/api/tools/tags/suggest")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_tag_suggest_with_query_parameter() -> None:
    """Test that tag suggest accepts query parameter."""
    response = client.get("/api/tools/tags/suggest?q=test")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_tag_suggest_returns_tags_from_created_tool() -> None:
    """Test that tag suggest returns tags from created tools."""
    # Create a tool with tags
    tool_data = {
        "name": "Test Tool for Tag Suggest",
        "description": "A test tool",
        "tags": ["tag1", "tag2", "tag3"],
        "html_content": "<html><body>Test</body></html>",
    }
    create_response = client.post("/api/tools/", json=tool_data)
    assert create_response.status_code == 201
    created_tool = create_response.json()

    # Check tag suggestions
    response = client.get("/api/tools/tags/suggest")
    assert response.status_code == 200
    tags = response.json()
    assert "tag1" in tags
    assert "tag2" in tags
    assert "tag3" in tags

    # Clean up
    client.delete(f"/api/tools/{created_tool['id']}")


def test_tag_suggest_filters_by_query() -> None:
    """Test that tag suggest filters tags by query."""
    # Create a tool with specific tags
    tool_data = {
        "name": "Filter Test Tool",
        "description": "A test tool",
        "tags": ["python", "javascript", "typescript"],
        "html_content": "<html><body>Test</body></html>",
    }
    create_response = client.post("/api/tools/", json=tool_data)
    assert create_response.status_code == 201
    created_tool = create_response.json()

    # Check tag suggestions with filter
    response = client.get("/api/tools/tags/suggest?q=script")
    assert response.status_code == 200
    tags = response.json()
    assert "javascript" in tags
    assert "typescript" in tags
    assert "python" not in tags

    # Clean up
    client.delete(f"/api/tools/{created_tool['id']}")
