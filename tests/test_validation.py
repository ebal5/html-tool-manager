"""バリデーションのテスト。"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from html_tool_manager.models.tool import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    TAG_MAX_LENGTH,
    TAGS_MAX_COUNT,
)


class TestNameValidation:
    """名前フィールドのバリデーションテスト。"""

    def test_empty_name_returns_422(self, session: Session, client: TestClient):
        """空の名前で422が返ることをテストする。"""
        tool_data = {"name": "", "description": "Desc", "html_content": "<p>test</p>"}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 422

    def test_whitespace_only_name_returns_422(self, session: Session, client: TestClient):
        """空白のみの名前で422が返ることをテストする。"""
        tool_data = {"name": "   ", "description": "Desc", "html_content": "<p>test</p>"}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 422

    def test_name_too_long_returns_422(self, session: Session, client: TestClient):
        """長すぎる名前で422が返ることをテストする。"""
        tool_data = {"name": "a" * (NAME_MAX_LENGTH + 1), "description": "Desc", "html_content": "<p>test</p>"}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 422

    def test_name_with_control_chars_returns_422(self, session: Session, client: TestClient):
        """制御文字を含む名前で422が返ることをテストする。"""
        tool_data = {"name": "test\x00name", "description": "Desc", "html_content": "<p>test</p>"}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 422

    def test_name_trimmed(self, session: Session, client: TestClient):
        """名前の前後の空白がトリムされることをテストする。"""
        tool_data = {"name": "  trimmed name  ", "description": "Desc", "html_content": "<p>test</p>"}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 201
        assert response.json()["name"] == "trimmed name"

    def test_valid_name_at_max_length(self, session: Session, client: TestClient):
        """最大長の名前が受け入れられることをテストする。"""
        tool_data = {"name": "a" * NAME_MAX_LENGTH, "description": "Desc", "html_content": "<p>test</p>"}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 201


class TestDescriptionValidation:
    """説明フィールドのバリデーションテスト。"""

    def test_description_too_long_returns_422(self, session: Session, client: TestClient):
        """長すぎる説明で422が返ることをテストする。"""
        tool_data = {"name": "Test", "description": "a" * (DESCRIPTION_MAX_LENGTH + 1), "html_content": "<p>test</p>"}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 422

    def test_description_with_control_chars_returns_422(self, session: Session, client: TestClient):
        """制御文字を含む説明で422が返ることをテストする。"""
        tool_data = {"name": "Test", "description": "desc\x00ription", "html_content": "<p>test</p>"}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 422

    def test_description_with_newline_allowed(self, session: Session, client: TestClient):
        """改行を含む説明が許可されることをテストする。"""
        tool_data = {"name": "Test", "description": "line1\nline2\ttabbed", "html_content": "<p>test</p>"}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 201

    def test_description_none_allowed(self, session: Session, client: TestClient):
        """説明がnullでも許可されることをテストする。"""
        tool_data = {"name": "Test", "description": None, "html_content": "<p>test</p>"}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 201


class TestQueryValidation:
    """検索クエリのバリデーションテスト。"""

    def test_query_too_long_returns_422(self, session: Session, client: TestClient):
        """長すぎる検索クエリで422が返ることをテストする。"""
        # max_length=500を超えるクエリ
        long_query = "a" * 501
        response = client.get(f"/api/tools/?q={long_query}")
        assert response.status_code == 422

    def test_query_at_max_length_accepted(self, session: Session, client: TestClient):
        """最大長の検索クエリが受け入れられることをテストする。"""
        # max_length=500のクエリ
        max_query = "a" * 500
        response = client.get(f"/api/tools/?q={max_query}")
        assert response.status_code == 200


class TestTagsValidation:
    """タグフィールドのバリデーションテスト。"""

    def test_too_many_tags_returns_422(self, session: Session, client: TestClient):
        """タグが多すぎると422が返ることをテストする。"""
        tags = [f"tag{i}" for i in range(TAGS_MAX_COUNT + 1)]
        tool_data = {"name": "Test", "description": "Desc", "html_content": "<p>test</p>", "tags": tags}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 422

    def test_tag_too_long_returns_422(self, session: Session, client: TestClient):
        """長すぎるタグで422が返ることをテストする。"""
        tool_data = {
            "name": "Test",
            "description": "Desc",
            "html_content": "<p>test</p>",
            "tags": ["a" * (TAG_MAX_LENGTH + 1)],
        }
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 422

    def test_tag_with_control_chars_returns_422(self, session: Session, client: TestClient):
        """制御文字を含むタグで422が返ることをテストする。"""
        tool_data = {"name": "Test", "description": "Desc", "html_content": "<p>test</p>", "tags": ["tag\x00name"]}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 422

    def test_empty_tags_skipped(self, session: Session, client: TestClient):
        """空のタグがスキップされることをテストする。"""
        tool_data = {"name": "Test", "description": "Desc", "html_content": "<p>test</p>", "tags": ["valid", "", "  "]}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 201
        assert response.json()["tags"] == ["valid"]

    def test_tags_trimmed(self, session: Session, client: TestClient):
        """タグの前後の空白がトリムされることをテストする。"""
        tool_data = {"name": "Test", "description": "Desc", "html_content": "<p>test</p>", "tags": ["  trimmed  "]}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 201
        assert response.json()["tags"] == ["trimmed"]

    def test_max_tags_allowed(self, session: Session, client: TestClient):
        """最大数のタグが許可されることをテストする。"""
        tags = [f"tag{i}" for i in range(TAGS_MAX_COUNT)]
        tool_data = {"name": "Test", "description": "Desc", "html_content": "<p>test</p>", "tags": tags}
        response = client.post("/api/tools/", json=tool_data)
        assert response.status_code == 201
        assert len(response.json()["tags"]) == TAGS_MAX_COUNT
