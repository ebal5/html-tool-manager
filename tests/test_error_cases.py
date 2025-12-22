"""エラーケースのテスト。"""

import msgpack
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_get_nonexistent_tool_returns_404(session: Session, client: TestClient):
    """存在しないツールIDでGETすると404が返ることをテストする。"""
    response = client.get("/api/tools/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Tool not found"


def test_update_nonexistent_tool_returns_404(session: Session, client: TestClient):
    """存在しないツールIDでPUTすると404が返ることをテストする。"""
    tool_data = {
        "name": "Updated",
        "description": "Updated desc",
        "html_content": "<p>updated</p>",
        "version": 1,
    }
    response = client.put("/api/tools/99999", json=tool_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Tool not found"


def test_delete_nonexistent_tool_returns_404(session: Session, client: TestClient):
    """存在しないツールIDでDELETEすると404が返ることをテストする。"""
    response = client.delete("/api/tools/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Tool not found"


def test_export_nonexistent_tools_returns_404(session: Session, client: TestClient):
    """存在しないツールIDでエクスポートすると404が返ることをテストする。"""
    response = client.post("/api/tools/export", json={"tool_ids": [99999, 99998]})
    assert response.status_code == 404
    assert response.json()["detail"] == "No exportable tools found."


def test_import_invalid_content_type_returns_415(session: Session, client: TestClient):
    """不正なcontent-typeでインポートすると415が返ることをテストする。"""
    response = client.post(
        "/api/tools/import",
        files={"file": ("test.txt", b"invalid data", "text/plain")},
    )
    assert response.status_code == 415
    assert response.json()["detail"] == "Unsupported file type."


def test_import_invalid_msgpack_returns_400(session: Session, client: TestClient):
    """不正なMessagePackデータでインポートすると400が返ることをテストする。"""
    response = client.post(
        "/api/tools/import",
        files={"file": ("test.pack", b"not a valid msgpack", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Invalid MessagePack file" in response.json()["detail"]


def test_import_with_invalid_tool_data_skips_invalid(session: Session, client: TestClient):
    """不正なツールデータを含むインポートは、不正なデータをスキップして処理することをテストする。"""
    tools_data = [
        {"name": "Valid Tool", "description": "Valid", "html_content": "<p>valid</p>"},
        {"invalid_field": "no name field"},  # 不正なデータ
        {"name": "Another Valid", "description": "Also valid", "html_content": "<p>also valid</p>"},
    ]
    packed = msgpack.packb(tools_data, use_bin_type=True)

    response = client.post(
        "/api/tools/import",
        files={"file": ("test.pack", packed, "application/octet-stream")},
    )
    assert response.status_code == 200
    # 不正なデータはスキップされ、2件のみインポートされる
    assert response.json()["imported_count"] == 2
