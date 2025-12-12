import msgpack
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_export_selected_tools(session: Session, client: TestClient):
    """Test that only selected tools are exported correctly."""
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
    """Test that tools can be imported from an exported file."""
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


def test_react_tool_export_import(session: Session, client: TestClient):
    """React ツールがエクスポート・インポートで tool_type を保持することをテスト。"""
    # React ツールを作成
    jsx_code = "import React from 'react';\nconst App = () => <div>Export Test</div>;"
    tool_data = {
        "name": "Export React Tool",
        "description": "React export test",
        "html_content": jsx_code,
        "tags": ["react", "export-test"],
    }

    create_response = client.post("/api/tools/", json=tool_data)
    assert create_response.status_code == 201
    tool_id = create_response.json()["id"]

    # エクスポート
    export_response = client.post("/api/tools/export", json={"tool_ids": [tool_id]})
    assert export_response.status_code == 200

    exported_data = msgpack.unpackb(export_response.content, raw=False)
    assert len(exported_data) == 1
    assert exported_data[0]["tool_type"] == "react"
    assert exported_data[0]["name"] == "Export React Tool"

    # DB をクリア
    client.delete(f"/api/tools/{tool_id}")

    # インポート
    import_response = client.post(
        "/api/tools/import",
        files={"file": ("tools.pack", export_response.content, "application/octet-stream")},
    )
    assert import_response.status_code == 200
    assert import_response.json()["imported_count"] == 1

    # インポートされたツールを確認
    list_response = client.get("/api/tools/")
    tools = list_response.json()
    imported_tool = next((t for t in tools if t["name"] == "Export React Tool"), None)

    assert imported_tool is not None
    assert imported_tool["tool_type"] == "react"
    assert imported_tool["description"] == "React export test"
    assert set(imported_tool["tags"]) == {"react", "export-test"}


def test_mixed_tools_export_import(session: Session, client: TestClient):
    """HTML と React の混在ツールをエクスポート・インポートできることをテスト。"""
    # HTML ツールを作成
    html_data = {
        "name": "HTML Export Tool",
        "html_content": "<p>HTML</p>",
        "tool_type": "html",
    }
    html_response = client.post("/api/tools/", json=html_data)
    html_id = html_response.json()["id"]

    # React ツールを作成
    jsx_data = {
        "name": "React Export Tool",
        "html_content": "import React from 'react';\nconst App = () => <div>React</div>;",
    }
    react_response = client.post("/api/tools/", json=jsx_data)
    react_id = react_response.json()["id"]

    # 両方をエクスポート
    export_response = client.post("/api/tools/export", json={"tool_ids": [html_id, react_id]})
    assert export_response.status_code == 200

    exported_data = msgpack.unpackb(export_response.content, raw=False)
    assert len(exported_data) == 2

    # tool_type が正しく含まれているか確認
    html_tool = next(t for t in exported_data if t["name"] == "HTML Export Tool")
    react_tool = next(t for t in exported_data if t["name"] == "React Export Tool")

    assert html_tool["tool_type"] == "html"
    assert react_tool["tool_type"] == "react"

    # DB をクリア
    client.delete(f"/api/tools/{html_id}")
    client.delete(f"/api/tools/{react_id}")

    # インポート
    import_response = client.post(
        "/api/tools/import",
        files={"file": ("tools.pack", export_response.content, "application/octet-stream")},
    )
    assert import_response.status_code == 200
    assert import_response.json()["imported_count"] == 2

    # インポート後のツールを確認
    list_response = client.get("/api/tools/")
    tools = list_response.json()

    html_imported = next((t for t in tools if t["name"] == "HTML Export Tool"), None)
    react_imported = next((t for t in tools if t["name"] == "React Export Tool"), None)

    assert html_imported is not None
    assert html_imported["tool_type"] == "html"
    assert react_imported is not None
    assert react_imported["tool_type"] == "react"
