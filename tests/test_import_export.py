import msgpack
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_export_selected_tools(session: Session, client: TestClient):
    """選択されたツールのみが正しくエクスポートされることをテストする。"""
    # 1. テストデータを作成 (API経由で)
    tool1_data = {"name": "Tool 1", "description": "Desc 1", "html_content": "<p>1</p>"}
    tool2_data = {"name": "Tool 2", "description": "Desc 2", "html_content": "<p>2</p>"}
    tool3_data = {"name": "Tool 3", "description": "Desc 3", "html_content": "<p>3</p>"}

    res1 = client.post("/api/tools/", json=tool1_data)
    res2 = client.post("/api/tools/", json=tool2_data)
    res3 = client.post("/api/tools/", json=tool3_data)

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res3.status_code == 201

    tool1_id = res1.json()["id"]
    tool3_id = res3.json()["id"]

    # 2. ツール1と3を選択してエクスポートAPIを呼び出す
    response = client.post("/api/tools/export", json={"tool_ids": [tool1_id, tool3_id]})

    # 3. レスポンスを検証
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"

    # 4. 内容をデシリアライズして検証
    exported_data = msgpack.unpackb(response.content, raw=False)

    assert len(exported_data) == 2

    exported_names = {item["name"] for item in exported_data}
    assert "Tool 1" in exported_names
    assert "Tool 3" in exported_names
    assert "Tool 2" not in exported_names

    # HTMLコンテンツも含まれているか確認
    # 順序は保証されないので、名前で検索する
    tool1_exported = next(item for item in exported_data if item["name"] == "Tool 1")
    assert tool1_exported["html_content"] == "<p>1</p>"


def test_import_tools(session: Session, client: TestClient):
    """エクスポートされたファイルをインポートできることをテストする。"""
    # 1. インポートするデータを作成 (MessagePack形式)
    tools_to_import = [
        {"name": "Imported Tool A", "description": "Import A", "tags": ["a"], "html_content": "<h1>A</h1>"},
        {"name": "Imported Tool B", "description": "Import B", "tags": ["b"], "html_content": "<h1>B</h1>"},
    ]
    packed_data = msgpack.packb(tools_to_import)

    # 2. インポートAPIを呼び出す
    response = client.post("/api/tools/import", files={"file": ("tools.pack", packed_data, "application/octet-stream")})

    # 3. レスポンスを検証
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["imported_count"] == 2

    # 4. ツールが実際にDBに作成されたかを確認
    all_tools_response = client.get("/api/tools/")
    all_tools = all_tools_response.json()

    assert len(all_tools) == 2

    db_names = {item["name"] for item in all_tools}
    assert "Imported Tool A" in db_names
    assert "Imported Tool B" in db_names
