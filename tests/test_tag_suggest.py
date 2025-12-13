"""Tests for the tag suggestion endpoint."""

from fastapi.testclient import TestClient
from sqlmodel import Session


def test_tag_suggest_returns_empty_list_when_no_tools(session: Session, client: TestClient) -> None:
    """Test that tag suggest returns empty list when no tools exist."""
    response = client.get("/api/tools/tags/suggest")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_tag_suggest_with_query_parameter(session: Session, client: TestClient) -> None:
    """Test that tag suggest accepts query parameter."""
    response = client.get("/api/tools/tags/suggest?q=test")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_tag_suggest_returns_tags_from_created_tool(session: Session, client: TestClient) -> None:
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


def test_tag_suggest_filters_by_query(session: Session, client: TestClient) -> None:
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


def test_tag_suggest_case_insensitive(session: Session, client: TestClient) -> None:
    """Test that tag suggest filtering is case-insensitive."""
    # Create a tool with mixed-case tags
    tool_data = {
        "name": "Case Test Tool",
        "description": "A test tool",
        "tags": ["JavaScript", "TypeScript", "PYTHON"],
        "html_content": "<html><body>Test</body></html>",
    }
    create_response = client.post("/api/tools/", json=tool_data)
    assert create_response.status_code == 201
    created_tool = create_response.json()

    # Query with lowercase should match uppercase tags
    response = client.get("/api/tools/tags/suggest?q=python")
    assert response.status_code == 200
    tags = response.json()
    assert "PYTHON" in tags

    # Query with uppercase should match mixed-case tags
    response = client.get("/api/tools/tags/suggest?q=SCRIPT")
    assert response.status_code == 200
    tags = response.json()
    assert "JavaScript" in tags
    assert "TypeScript" in tags

    # Clean up
    client.delete(f"/api/tools/{created_tool['id']}")


def test_tag_suggest_escapes_sql_wildcards(session: Session, client: TestClient) -> None:
    """Test that SQL wildcard characters are properly escaped."""
    # Create a tool with tags containing SQL wildcards
    tool_data = {
        "name": "Wildcard Test Tool",
        "description": "A test tool",
        "tags": ["100%", "__init__", "a%b", "normal"],
        "html_content": "<html><body>Test</body></html>",
    }
    create_response = client.post("/api/tools/", json=tool_data)
    assert create_response.status_code == 201
    created_tool = create_response.json()

    # Query with % should match literal % only, not as wildcard
    response = client.get("/api/tools/tags/suggest?q=%25")  # URL encoded %
    assert response.status_code == 200
    tags = response.json()
    assert "100%" in tags
    assert "a%b" in tags
    assert "normal" not in tags  # Should not match (no % in tag)

    # Query with _ should match literal _ only, not as wildcard
    response = client.get("/api/tools/tags/suggest?q=_")
    assert response.status_code == 200
    tags = response.json()
    assert "__init__" in tags
    assert "normal" not in tags  # Should not match (no _ in tag)

    # Clean up
    client.delete(f"/api/tools/{created_tool['id']}")
