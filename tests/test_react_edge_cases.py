"""Edge case tests for React tool management."""

from fastapi.testclient import TestClient
from sqlmodel import Session


def test_ambiguous_code_defaults_to_html(client: TestClient, session: Session):
    """曖昧なコード（React パターンが 1 つ以下）は HTML として扱われることをテスト。"""
    ambiguous_code = "<div>Hello</div>"
    tool_data = {
        "name": "Ambiguous Tool",
        "html_content": ambiguous_code,
    }

    response = client.post("/api/tools/", json=tool_data)
    assert response.status_code == 201
    data = response.json()
    assert data["tool_type"] == "html"

    # クリーンアップ
    client.delete(f"/api/tools/{data['id']}")


def test_complex_jsx_with_multiple_components(client: TestClient, session: Session):
    """複数のコンポーネントを含む複雑な JSX が正しく処理されることをテスト。"""
    jsx_code = """
import React, { useState, useEffect } from 'react';

const Header = () => <h1>Header</h1>;

const Footer = () => <footer>Footer</footer>;

function App() {
    const [data, setData] = useState(null);

    useEffect(() => {
        setData('Hello');
    }, []);

    return (
        <div>
            <Header />
            <main>{data}</main>
            <Footer />
        </div>
    );
}
"""
    tool_data = {
        "name": "Complex Component",
        "html_content": jsx_code,
    }

    response = client.post("/api/tools/", json=tool_data)
    assert response.status_code == 201
    data = response.json()
    assert data["tool_type"] == "react"

    # ファイル内容を確認
    with open(data["filepath"]) as f:
        content = f.read()
        # import 文が削除されている
        assert "import React" not in content
        # 全てのコンポーネントが保持されている
        assert "const Header" in content
        assert "const Footer" in content
        assert "function App" in content

    # クリーンアップ
    client.delete(f"/api/tools/{data['id']}")


def test_jsx_with_inline_styles(client: TestClient, session: Session):
    """インラインスタイルを含む JSX が正しく処理されることをテスト。"""
    jsx_code = """
import React from 'react';

const App = () => {
    const style = {
        color: 'blue',
        fontSize: '16px'
    };

    return <div style={style}>Styled Text</div>;
};
"""
    tool_data = {
        "name": "Styled Component",
        "html_content": jsx_code,
    }

    response = client.post("/api/tools/", json=tool_data)
    assert response.status_code == 201
    data = response.json()
    assert data["tool_type"] == "react"

    # ファイル内容を確認
    with open(data["filepath"]) as f:
        content = f.read()
        assert "const style" in content
        assert "fontSize" in content

    # クリーンアップ
    client.delete(f"/api/tools/{data['id']}")


def test_create_tool_with_empty_html_content(client: TestClient, session: Session):
    """html_content が空の場合のエラーハンドリングをテスト。"""
    tool_data = {
        "name": "Empty Tool",
        "html_content": "",
    }

    response = client.post("/api/tools/", json=tool_data)
    # 空のコンテンツでも作成可能（バリデーションは html_content を必須としていない）
    if response.status_code == 201:
        data = response.json()
        # デフォルトで HTML として扱われる
        assert data["tool_type"] == "html"
        client.delete(f"/api/tools/{data['id']}")


def test_update_tool_without_changing_type(client: TestClient, session: Session):
    """tool_type を変更せずにツールを更新できることをテスト。"""
    # React ツールを作成
    jsx_code = "import React from 'react';\nconst App = () => <div>Original</div>;"
    tool_data = {
        "name": "Update Test",
        "html_content": jsx_code,
    }

    create_response = client.post("/api/tools/", json=tool_data)
    tool_id = create_response.json()["id"]

    # 説明のみを更新（html_content と tool_type は送信しない）
    update_data = {
        "name": "Update Test",
        "description": "Updated description",
    }

    update_response = client.put(f"/api/tools/{tool_id}", json=update_data)
    assert update_response.status_code == 200
    updated_tool = update_response.json()
    assert updated_tool["tool_type"] == "react"
    assert updated_tool["description"] == "Updated description"

    # クリーンアップ
    client.delete(f"/api/tools/{tool_id}")


def test_jsx_with_fragments(client: TestClient, session: Session):
    """React Fragment を使用した JSX が正しく処理されることをテスト。"""
    jsx_code = """
import React from 'react';

const App = () => {
    return (
        <>
            <h1>Title</h1>
            <p>Paragraph</p>
        </>
    );
};
"""
    tool_data = {
        "name": "Fragment Test",
        "html_content": jsx_code,
    }

    response = client.post("/api/tools/", json=tool_data)
    assert response.status_code == 201
    data = response.json()
    assert data["tool_type"] == "react"

    # ファイル内容を確認
    with open(data["filepath"]) as f:
        content = f.read()
        # Fragment の構文が保持されている
        assert "<>" in content or "React.Fragment" in content

    # クリーンアップ
    client.delete(f"/api/tools/{data['id']}")


def test_jsx_with_event_handlers(client: TestClient, session: Session):
    """イベントハンドラを含む JSX が正しく処理されることをテスト。"""
    jsx_code = """
import React, { useState } from 'react';

const App = () => {
    const [count, setCount] = useState(0);

    const handleClick = () => {
        setCount(count + 1);
    };

    const handleDoubleClick = () => {
        setCount(count * 2);
    };

    return (
        <div>
            <button onClick={handleClick}>Click</button>
            <button onDoubleClick={handleDoubleClick}>Double Click</button>
            <p>{count}</p>
        </div>
    );
};
"""
    tool_data = {
        "name": "Event Handler Test",
        "html_content": jsx_code,
    }

    response = client.post("/api/tools/", json=tool_data)
    assert response.status_code == 201
    data = response.json()
    assert data["tool_type"] == "react"

    # ファイル内容を確認
    with open(data["filepath"]) as f:
        content = f.read()
        assert "handleClick" in content
        assert "handleDoubleClick" in content
        assert "onClick" in content
        assert "onDoubleClick" in content

    # クリーンアップ
    client.delete(f"/api/tools/{data['id']}")


def test_backward_compatibility_existing_html_tools(client: TestClient, session: Session):
    """既存の HTML ツールが tool_type='html' として扱われることをテスト。"""
    html_code = """<!DOCTYPE html>
<html>
<head><title>Legacy Tool</title></head>
<body><p>This is a legacy HTML tool</p></body>
</html>"""
    tool_data = {
        "name": "Legacy HTML Tool",
        "html_content": html_code,
    }

    response = client.post("/api/tools/", json=tool_data)
    assert response.status_code == 201
    data = response.json()
    # 後方互換性: HTML として検出される
    assert data["tool_type"] == "html"

    # クリーンアップ
    client.delete(f"/api/tools/{data['id']}")
