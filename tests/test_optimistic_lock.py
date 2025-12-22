"""楽観的ロック機能のテスト。"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from html_tool_manager.core.exceptions import OptimisticLockError
from html_tool_manager.models import ToolCreate
from html_tool_manager.repositories import ToolRepository


class TestOptimisticLockModel:
    """モデル層のバージョンフィールドテスト。"""

    def test_tool_has_default_version(self, session: Session, client: TestClient, test_tools_dir):
        """新規作成ツールのバージョンがデフォルト1であることをテスト。"""
        response = client.post("/api/tools/", json={"name": "Test Tool", "html_content": "<p>test</p>"})
        assert response.status_code == 201
        assert response.json()["version"] == 1

    def test_version_increments_on_update(self, session: Session, client: TestClient, test_tools_dir):
        """更新時にバージョンがインクリメントされることをテスト。"""
        # 作成
        create_response = client.post("/api/tools/", json={"name": "Test Tool", "html_content": "<p>test</p>"})
        tool_id = create_response.json()["id"]

        # 更新
        update_response = client.put(
            f"/api/tools/{tool_id}",
            json={
                "name": "Updated Tool",
                "html_content": "<p>updated</p>",
                "version": 1,
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["version"] == 2


class TestOptimisticLockConflict:
    """楽観的ロック競合のテスト。"""

    def test_conflict_returns_409(self, session: Session, client: TestClient, test_tools_dir):
        """バージョン不一致で409が返ることをテスト。"""
        # 作成
        create_response = client.post("/api/tools/", json={"name": "Test Tool", "html_content": "<p>test</p>"})
        tool_id = create_response.json()["id"]

        # 先に更新（バージョン1→2）
        client.put(
            f"/api/tools/{tool_id}",
            json={
                "name": "First Update",
                "html_content": "<p>first</p>",
                "version": 1,
            },
        )

        # 古いバージョンで更新を試みる
        conflict_response = client.put(
            f"/api/tools/{tool_id}",
            json={
                "name": "Second Update",
                "html_content": "<p>second</p>",
                "version": 1,  # 古いバージョン
            },
        )

        assert conflict_response.status_code == 409
        detail = conflict_response.json()["detail"]
        assert detail["error_code"] == "OPTIMISTIC_LOCK_CONFLICT"
        assert detail["current_version"] == 2
        assert detail["your_version"] == 1

    def test_correct_version_succeeds(self, session: Session, client: TestClient, test_tools_dir):
        """正しいバージョンで更新が成功することをテスト。"""
        # 作成
        create_response = client.post("/api/tools/", json={"name": "Test Tool", "html_content": "<p>test</p>"})
        tool_id = create_response.json()["id"]
        version = create_response.json()["version"]

        # 正しいバージョンで更新
        update_response = client.put(
            f"/api/tools/{tool_id}",
            json={
                "name": "Updated Tool",
                "html_content": "<p>updated</p>",
                "version": version,
            },
        )

        assert update_response.status_code == 200

    def test_conflict_error_message(self, session: Session, client: TestClient, test_tools_dir):
        """409エラーに適切なメッセージが含まれることをテスト。"""
        # 作成
        create_response = client.post("/api/tools/", json={"name": "Test Tool", "html_content": "<p>test</p>"})
        tool_id = create_response.json()["id"]

        # 先に更新
        client.put(
            f"/api/tools/{tool_id}",
            json={
                "name": "First Update",
                "html_content": "<p>first</p>",
                "version": 1,
            },
        )

        # 古いバージョンで更新を試みる
        conflict_response = client.put(
            f"/api/tools/{tool_id}",
            json={
                "name": "Second Update",
                "html_content": "<p>second</p>",
                "version": 1,
            },
        )

        detail = conflict_response.json()["detail"]
        assert "message" in detail
        assert "他のユーザー" in detail["message"]


class TestOptimisticLockRepository:
    """リポジトリ層の楽観的ロックテスト。"""

    def test_repository_raises_exception_on_conflict(self, session: Session, test_tools_dir):
        """リポジトリがバージョン不一致時に例外を発生させることをテスト。"""
        repo = ToolRepository(session)

        # ツール作成
        tool = repo.create_tool_with_content(ToolCreate(name="Test", html_content="<p>test</p>"))
        original_version = tool.version

        # 直接DBでバージョンを変更（別プロセスによる更新をシミュレート）
        tool.version = 99
        session.add(tool)
        session.commit()

        # 古いバージョンで更新を試みる
        with pytest.raises(OptimisticLockError) as exc_info:
            repo.update_tool(tool.id, tool, expected_version=original_version)

        assert exc_info.value.current_version == 99
        assert exc_info.value.expected_version == original_version

    def test_repository_increments_version_on_success(self, session: Session, test_tools_dir):
        """リポジトリが更新成功時にバージョンをインクリメントすることをテスト。"""
        repo = ToolRepository(session)

        # ツール作成
        tool = repo.create_tool_with_content(ToolCreate(name="Test", html_content="<p>test</p>"))
        assert tool.version == 1

        # 更新
        tool.name = "Updated"
        updated_tool = repo.update_tool(tool.id, tool, expected_version=1)

        assert updated_tool is not None
        assert updated_tool.version == 2


class TestVersionRequirement:
    """versionフィールド必須のテスト。"""

    def test_update_without_version_fails(self, session: Session, client: TestClient, test_tools_dir):
        """versionなしの更新リクエストが422エラーになることをテスト。"""
        # 作成
        create_response = client.post("/api/tools/", json={"name": "Test Tool", "html_content": "<p>test</p>"})
        tool_id = create_response.json()["id"]

        # versionなしで更新を試みる
        update_response = client.put(
            f"/api/tools/{tool_id}",
            json={
                "name": "Updated Tool",
                "html_content": "<p>updated</p>",
                # version フィールドなし
            },
        )

        # ToolUpdateモデルでversionが必須なので422 Unprocessable Entityになるはず
        assert update_response.status_code == 422
