"""Tests for template library API endpoints."""

from fastapi.testclient import TestClient


class TestListTemplates:
    """Tests for GET /api/templates/ endpoint."""

    def test_list_templates_returns_templates_and_categories(self, client: TestClient):
        """Test that list templates returns both templates and categories."""
        response = client.get("/api/templates/")
        assert response.status_code == 200

        data = response.json()
        assert "templates" in data
        assert "categories" in data
        assert len(data["templates"]) > 0
        assert len(data["categories"]) > 0

    def test_list_templates_template_structure(self, client: TestClient):
        """Test that each template has required fields."""
        response = client.get("/api/templates/")
        assert response.status_code == 200

        templates = response.json()["templates"]
        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "category" in template
            assert "tags" in template
            assert "tool_type" in template
            assert isinstance(template["tags"], list)

    def test_list_templates_category_structure(self, client: TestClient):
        """Test that each category has required fields."""
        response = client.get("/api/templates/")
        assert response.status_code == 200

        categories = response.json()["categories"]
        for category in categories.values():
            assert "name" in category
            assert "description" in category

    def test_list_templates_has_expected_categories(self, client: TestClient):
        """Test that expected categories exist."""
        response = client.get("/api/templates/")
        assert response.status_code == 200

        categories = response.json()["categories"]
        expected_categories = ["transform", "generate", "text", "dev"]
        for cat in expected_categories:
            assert cat in categories


class TestAddTemplate:
    """Tests for POST /api/templates/{template_id}/add endpoint."""

    def test_add_template_creates_tool(self, client: TestClient):
        """Test that adding a template creates a new tool."""
        response = client.post("/api/templates/json-formatter/add", json={})
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["name"] == "JSON整形ツール"
        assert "filepath" in data
        assert data["tool_type"] == "html"

    def test_add_template_with_custom_name(self, client: TestClient):
        """Test that adding a template with custom name works."""
        response = client.post(
            "/api/templates/base64-encoder/add",
            json={"custom_name": "My Base64 Tool"},
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "My Base64 Tool"

    def test_add_template_not_found(self, client: TestClient):
        """Test that adding non-existent template returns 404."""
        response = client.post("/api/templates/nonexistent-template/add", json={})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_add_template_preserves_tags(self, client: TestClient):
        """Test that tags are preserved when adding a template."""
        response = client.post("/api/templates/uuid-generator/add", json={})
        assert response.status_code == 201

        data = response.json()
        assert "UUID" in data["tags"]
        assert "ID" in data["tags"]

    def test_add_template_preserves_description(self, client: TestClient):
        """Test that description is preserved when adding a template."""
        response = client.post("/api/templates/char-counter/add", json={})
        assert response.status_code == 201

        data = response.json()
        assert "文字数" in data["description"]

    def test_added_tool_is_retrievable(self, client: TestClient):
        """Test that a tool added from template can be retrieved."""
        # Add template
        add_response = client.post("/api/templates/color-picker/add", json={})
        assert add_response.status_code == 201
        tool_id = add_response.json()["id"]

        # Retrieve the tool
        get_response = client.get(f"/api/tools/{tool_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "カラーピッカー"


class TestTemplatesPage:
    """Tests for /templates page endpoint."""

    def test_templates_page_returns_html(self, client: TestClient):
        """Test that templates page returns HTML."""
        response = client.get("/templates")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_templates_page_contains_gallery(self, client: TestClient):
        """Test that templates page contains gallery element."""
        response = client.get("/templates")
        assert response.status_code == 200
        assert "templates-gallery" in response.text
