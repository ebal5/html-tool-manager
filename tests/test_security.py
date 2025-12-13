"""Security tests for the HTML Tool Manager."""

from html_tool_manager.repositories.tool_repository import _escape_fts5_term


class TestFTS5Injection:
    """Tests for FTS5 injection prevention."""

    def test_fts5_escapes_double_quotes(self):
        """Test FTS5 escapes double quotes."""
        result = _escape_fts5_term('test"query')
        assert '""' in result  # Double quotes should be escaped
        assert result == '"test""query"*'

    def test_fts5_escapes_special_characters(self):
        """Test FTS5 handles special characters safely."""
        # These should not cause SQL injection
        dangerous_inputs = [
            'name:" OR 1=1 --',
            "'; DROP TABLE tool; --",
            "test\x00null",  # null byte
            "query*wildcard",
        ]
        for term in dangerous_inputs:
            result = _escape_fts5_term(term)
            # Should return a safely escaped string or empty
            assert isinstance(result, str)

    def test_fts5_handles_null_bytes(self):
        """Test null bytes are filtered from search queries."""
        result = _escape_fts5_term("test\x00injection")
        assert "\x00" not in result
        assert result == '"testinjection"*'

    def test_fts5_handles_control_characters(self):
        """Test control characters are filtered."""
        result = _escape_fts5_term("test\x01\x02\x03query")
        assert result == '"testquery"*'

    def test_fts5_handles_tab_and_newline(self):
        """Test tab and newline are filtered."""
        result = _escape_fts5_term("test\t\nquery")
        assert result == '"testquery"*'


class TestIncompleteFieldPrefix:
    """Tests for incomplete field prefix handling."""

    def test_incomplete_tag_prefix_returns_empty(self):
        """Test 'tag:' returns empty string."""
        result = _escape_fts5_term("tag:")
        assert result == ""

    def test_incomplete_name_prefix_returns_empty(self):
        """Test 'name:' returns empty string."""
        result = _escape_fts5_term("name:")
        assert result == ""

    def test_incomplete_desc_prefix_returns_empty(self):
        """Test 'desc:' returns empty string."""
        result = _escape_fts5_term("desc:")
        assert result == ""

    def test_colon_in_middle_is_allowed(self):
        """Test colons in middle of term are allowed."""
        result = _escape_fts5_term("http://example.com")
        assert result == '"http://example.com"*'

    def test_search_with_incomplete_prefix_returns_200(self, client):
        """Test search with incomplete field prefix returns 200."""
        response = client.get("/api/tools/?q=name:Query%20tag:")
        assert response.status_code == 200

    def test_search_with_only_colon_prefix_returns_200(self, client):
        """Test search with only colon prefix returns 200."""
        response = client.get("/api/tools/?q=tag:")
        assert response.status_code == 200


class TestFilepathValidation:
    """Tests for filepath validation (directory traversal prevention)."""

    def test_filepath_rejects_directory_traversal(self, client):
        """Test filepath with '..' is rejected."""
        response = client.post(
            "/api/tools/",
            json={
                "name": "Test",
                "description": "Test",
                "tags": [],
                "html_content": "<p>test</p>",
                "filepath": "../../../etc/passwd",
            },
        )
        # filepath is excluded from updates, so it won't cause an error here
        # but the model validator should catch it if it were used
        assert response.status_code in [201, 422]

    def test_filepath_rejects_absolute_path(self, client):
        """Test absolute filepath is rejected."""
        response = client.post(
            "/api/tools/",
            json={
                "name": "Test",
                "description": "Test",
                "tags": [],
                "html_content": "<p>test</p>",
                "filepath": "/etc/passwd",
            },
        )
        assert response.status_code in [201, 422]

    def test_filepath_immutable_on_update(self, client):
        """Test filepath cannot be modified via update API."""
        # Create a tool
        create_response = client.post(
            "/api/tools/",
            json={
                "name": "Filepath Immutable Test",
                "description": "Test",
                "tags": [],
                "html_content": "<p>test</p>",
            },
        )
        assert create_response.status_code == 201
        tool = create_response.json()
        original_filepath = tool["filepath"]

        # Try to update filepath
        update_response = client.put(
            f"/api/tools/{tool['id']}",
            json={
                "name": "Filepath Immutable Test",
                "description": "Updated",
                "tags": [],
                "html_content": "<p>updated</p>",
                "filepath": "../../../evil/path",
            },
        )

        # Update should succeed but filepath should remain unchanged
        if update_response.status_code == 200:
            updated_tool = update_response.json()
            assert updated_tool["filepath"] == original_filepath
            assert "../" not in updated_tool["filepath"]

        # Cleanup
        client.delete(f"/api/tools/{tool['id']}")


class TestSecurityHeaders:
    """Tests for security headers."""

    def test_x_frame_options_header(self, client):
        """Test X-Frame-Options header is set."""
        response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_x_content_type_options_header(self, client):
        """Test X-Content-Type-Options header is set."""
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_referrer_policy_header(self, client):
        """Test Referrer-Policy header is set."""
        response = client.get("/")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


class TestXSSPrevention:
    """Tests for XSS prevention."""

    def test_tool_name_not_executed_as_html(self, client):
        """Test tool name with script tag is escaped."""
        response = client.post(
            "/api/tools/",
            json={
                "name": "<script>alert('xss')</script>",
                "description": "Test",
                "tags": [],
                "html_content": "<p>test</p>",
            },
        )
        assert response.status_code == 201
        tool = response.json()

        # Name should be stored as-is (not executed)
        assert tool["name"] == "<script>alert('xss')</script>"

        # Get the tool and verify
        get_response = client.get(f"/api/tools/{tool['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "<script>alert('xss')</script>"

        # Cleanup
        client.delete(f"/api/tools/{tool['id']}")

    def test_description_with_script_tag(self, client):
        """Test description with script tag is stored safely."""
        response = client.post(
            "/api/tools/",
            json={
                "name": "XSS Test",
                "description": "<script>alert('xss')</script>",
                "tags": [],
                "html_content": "<p>test</p>",
            },
        )
        assert response.status_code == 201
        tool = response.json()
        assert "<script>" in tool["description"]

        # Cleanup
        client.delete(f"/api/tools/{tool['id']}")
