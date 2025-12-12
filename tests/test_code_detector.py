"""Tests for code type detection."""

from html_tool_manager.models.tool import ToolType
from html_tool_manager.utils.code_detector import detect_tool_type


def test_detect_html_with_doctype():
    """DOCTYPE 宣言を含むコードは HTML と検出されることをテスト。"""
    code = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><p>Hello</p></body>
</html>"""
    assert detect_tool_type(code) == ToolType.HTML


def test_detect_html_with_html_tag():
    """<html> タグを含むコードは HTML と検出されることをテスト。"""
    code = "<html><body>Test</body></html>"
    assert detect_tool_type(code) == ToolType.HTML


def test_detect_react_with_jsx_and_hooks():
    """JSX と hooks を含むコードは React と検出されることをテスト。"""
    code = """
import React, { useState } from 'react';

function App() {
    const [count, setCount] = useState(0);
    return <div onClick={() => setCount(count + 1)}>{count}</div>;
}
"""
    assert detect_tool_type(code) == ToolType.REACT


def test_detect_react_with_component_and_reactdom():
    """JSX コンポーネントと ReactDOM.render を含むコードは React と検出されることをテスト。"""
    code = """
import ReactDOM from 'react-dom';

function MyComponent() {
    return <div>Hello</div>;
}

ReactDOM.render(<MyComponent />, document.getElementById('root'));
"""
    assert detect_tool_type(code) == ToolType.REACT


def test_detect_html_for_simple_jsx_without_react_patterns():
    """React パターンが 1 つ以下の場合は HTML と検出されることをテスト。"""
    code = "<div>Simple HTML</div>"
    assert detect_tool_type(code) == ToolType.HTML


def test_detect_react_with_arrow_function_component():
    """アロー関数コンポーネントは React と検出されることをテスト。"""
    code = """
import React from 'react';

const App = () => {
    return <div>Arrow Function Component</div>;
};
"""
    assert detect_tool_type(code) == ToolType.REACT


def test_detect_react_edge_case_exactly_two_patterns():
    """ちょうど 2 つの React パターンにマッチする場合をテスト。"""
    code = """
import React from 'react';
const MyComponent = () => <div>Test</div>;
"""
    assert detect_tool_type(code) == ToolType.REACT


def test_detect_react_with_hooks_only():
    """Hooks だけでも React と検出されることをテスト。"""
    code = """
import { useState, useEffect } from 'react';

function App() {
    const [data, setData] = useState(null);
    useEffect(() => {
        // Some effect
    }, []);
    return <div>{data}</div>;
}
"""
    assert detect_tool_type(code) == ToolType.REACT
