"""Integration tests for React tool management."""

import os

from fastapi.testclient import TestClient
from sqlmodel import Session


def test_create_react_tool_auto_detection(client: TestClient, session: Session):
    """React コードが自動検出され、React ツールとして作成されることをテスト。"""
    jsx_code = """
import React, { useState } from 'react';

function App() {
    const [count, setCount] = useState(0);
    return (
        <div>
            <p>Count: {count}</p>
            <button onClick={() => setCount(count + 1)}>Increment</button>
        </div>
    );
}
"""
    tool_data = {
        "name": "Counter App",
        "description": "A simple counter",
        "html_content": jsx_code,
        # tool_type を指定しない → 自動検出
    }

    response = client.post("/api/tools/", json=tool_data)
    assert response.status_code == 201

    data = response.json()
    assert data["tool_type"] == "react"
    assert data["name"] == "Counter App"

    # ファイルが実際に作成されているか確認
    assert os.path.exists(data["filepath"])

    # ファイル内容を確認
    with open(data["filepath"]) as f:
        content = f.read()
        assert "<!DOCTYPE html>" in content
        assert "react@18.2.0" in content
        assert "@babel/standalone@7.23.5" in content
        # 元の JSX コードは変換されている
        assert "function App" in content
        # import 文は削除されている
        assert "import React" not in content

    # クリーンアップ
    client.delete(f"/api/tools/{data['id']}")


def test_create_react_tool_explicit_type(client: TestClient, session: Session):
    """tool_type を react に明示的に指定して React ツールを作成できることをテスト。"""
    jsx_code = "const App = () => <div>Test</div>;"
    tool_data = {
        "name": "Test React Tool",
        "description": "Explicit React type",
        "html_content": jsx_code,
        "tool_type": "react",  # 明示的に指定
    }

    response = client.post("/api/tools/", json=tool_data)
    assert response.status_code == 201
    data = response.json()
    assert data["tool_type"] == "react"

    # ファイル内容を確認
    with open(data["filepath"]) as f:
        content = f.read()
        assert "react@18.2.0" in content
        assert "const App" in content

    # クリーンアップ
    client.delete(f"/api/tools/{data['id']}")


def test_create_html_tool_with_html_content(client: TestClient, session: Session):
    """HTML コンテンツは自動的に HTML ツールとして作成されることをテスト。"""
    html_code = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><p>Hello HTML</p></body>
</html>"""
    tool_data = {
        "name": "HTML Tool",
        "description": "An HTML tool",
        "html_content": html_code,
    }

    response = client.post("/api/tools/", json=tool_data)
    assert response.status_code == 201
    data = response.json()
    assert data["tool_type"] == "html"

    # クリーンアップ
    client.delete(f"/api/tools/{data['id']}")


def test_react_tool_appears_in_list(client: TestClient, session: Session):
    """React ツールが一覧に表示されることをテスト。"""
    # React ツールを作成
    jsx_code = """
import React, { useState } from 'react';
function App() { return <div>Test</div>; }
"""
    tool_data = {
        "name": "List Test React Tool",
        "html_content": jsx_code,
    }

    create_response = client.post("/api/tools/", json=tool_data)
    assert create_response.status_code == 201
    tool_id = create_response.json()["id"]

    # 一覧を取得
    list_response = client.get("/api/tools/")
    assert list_response.status_code == 200

    tools = list_response.json()
    react_tool = next((t for t in tools if t["id"] == tool_id), None)

    assert react_tool is not None
    assert react_tool["tool_type"] == "react"
    assert react_tool["name"] == "List Test React Tool"

    # クリーンアップ
    client.delete(f"/api/tools/{tool_id}")


def test_update_tool_type_html_to_react(client: TestClient, session: Session):
    """ツールタイプを HTML から React に変更できることをテスト。"""
    # まず HTML ツールを作成
    html_data = {
        "name": "Test Tool",
        "description": "Initially HTML",
        "html_content": "<p>Hello</p>",
        "tool_type": "html",
    }
    create_response = client.post("/api/tools/", json=html_data)
    assert create_response.status_code == 201
    tool_id = create_response.json()["id"]

    # React コードに更新
    jsx_code = """
import React from 'react';
const App = () => <div>Updated to React</div>;
"""
    update_data = {
        "name": "Test Tool",
        "description": "Now React",
        "html_content": jsx_code,
        "tool_type": "react",
    }
    update_response = client.put(f"/api/tools/{tool_id}", json=update_data)
    assert update_response.status_code == 200

    updated_tool = update_response.json()
    assert updated_tool["tool_type"] == "react"

    # ファイルが React テンプレートでラップされているか確認
    with open(updated_tool["filepath"]) as f:
        content = f.read()
        assert "react@18.2.0" in content
        assert "<!DOCTYPE html>" in content
        # import 文は削除されている
        assert "import React" not in content

    # クリーンアップ
    client.delete(f"/api/tools/{tool_id}")


def test_mixed_tools_list(client: TestClient, session: Session):
    """HTML ツールと React ツールが混在した一覧が正しく返ることをテスト。"""
    # HTML ツールを作成
    html_data = {"name": "HTML Tool", "html_content": "<p>HTML</p>"}
    html_response = client.post("/api/tools/", json=html_data)
    html_id = html_response.json()["id"]

    # React ツールを作成
    jsx_data = {
        "name": "React Tool",
        "html_content": "import React from 'react';\nconst App = () => <div>React</div>;",
    }
    react_response = client.post("/api/tools/", json=jsx_data)
    react_id = react_response.json()["id"]

    # 一覧を取得
    response = client.get("/api/tools/")
    tools = response.json()

    html_tool = next(t for t in tools if t["id"] == html_id)
    react_tool = next(t for t in tools if t["id"] == react_id)

    assert html_tool["tool_type"] == "html"
    assert react_tool["tool_type"] == "react"

    # クリーンアップ
    client.delete(f"/api/tools/{html_id}")
    client.delete(f"/api/tools/{react_id}")
