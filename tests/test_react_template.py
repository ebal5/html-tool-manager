"""Tests for React template generation."""

from html_tool_manager.templates.react_template import (
    _transform_imports_exports,
    generate_react_html,
)


def test_generate_react_html_basic():
    """基本的な React HTML 生成のテスト。"""
    jsx_code = """
function App() {
    return <div>Hello React!</div>;
}
"""
    result = generate_react_html(jsx_code)

    assert "<!DOCTYPE html>" in result
    assert "react@18.2.0" in result
    assert "react-dom@18.2.0" in result
    assert "@babel/standalone@7.23.5" in result
    assert "Hello React!" in result
    assert "ReactDOM.createRoot" in result


def test_transform_imports_exports_removes_react_imports():
    """React import が削除されることをテスト。"""
    code = """
import React, { useState } from 'react';
import ReactDOM from 'react-dom';

function App() {
    return <div>Test</div>;
}
"""
    result = _transform_imports_exports(code)

    assert "import React" not in result
    assert "import ReactDOM" not in result
    assert "function App()" in result


def test_transform_exports_converts_export_default():
    """Export default が function App に変換されることをテスト。"""
    code = """
export default function MyComponent() {
    return <div>Test</div>;
}
"""
    result = _transform_imports_exports(code)

    assert "export default" not in result
    assert "function App" in result


def test_transform_removes_named_exports():
    """Named export が削除されることをテスト。"""
    code = """
export const helper = () => {};
export function App() {
    return <div>Test</div>;
}
"""
    result = _transform_imports_exports(code)

    assert "export const" not in result
    assert "export function" not in result


def test_transform_handles_single_quotes_and_double_quotes():
    """シングルクォートとダブルクォートの両方が処理されることをテスト。"""
    code1 = 'import React from "react";'
    code2 = "import React from 'react';"

    result1 = _transform_imports_exports(code1)
    result2 = _transform_imports_exports(code2)

    assert "import" not in result1
    assert "import" not in result2


def test_transform_preserves_non_react_code():
    """React 以外のコードが保持されることをテスト。"""
    code = """
const helper = (x) => x * 2;

function App() {
    return <div>{helper(5)}</div>;
}
"""
    result = _transform_imports_exports(code)
    assert "const helper" in result


def test_transform_arrow_function_export():
    """Arrow function export が const App に変換されることをテスト。"""
    code = """
export default const MyComponent = () => {
    return <div>Test</div>;
};
"""
    result = _transform_imports_exports(code)

    assert "export default" not in result
    assert "const App =" in result


def test_transform_standalone_export_default():
    """単独の export default Name; が削除されることをテスト。"""
    code = """
function MyComponent() {
    return <div>Test</div>;
}

export default MyComponent;
"""
    result = _transform_imports_exports(code)

    assert "export default" not in result
    assert "function MyComponent" in result


def test_react18_hooks_included_in_template():
    """React 18 の hooks がテンプレートに含まれることをテスト。"""
    jsx_code = "function App() { return <div>Test</div>; }"
    result = generate_react_html(jsx_code)

    # 基本 hooks
    assert "useState" in result
    assert "useEffect" in result
    assert "useCallback" in result
    assert "useMemo" in result
    assert "useRef" in result

    # 追加 hooks
    assert "useLayoutEffect" in result
    assert "useImperativeHandle" in result

    # React 18 hooks
    assert "useTransition" in result
    assert "useDeferredValue" in result
    assert "useId" in result


def test_script_tag_escaped_to_prevent_xss():
    """</script>タグがエスケープされてXSS攻撃を防ぐことをテスト。"""
    # 正常なテンプレートの</script>数を基準として取得
    normal_jsx = "function App() { return <div>Test</div>; }"
    normal_result = generate_react_html(normal_jsx)
    normal_script_count = normal_result.count("</script>")

    # 悪意のあるコードを含むJSXコード（</script>を含む）
    malicious_jsx = """
function App() {
    const msg = '</script><script>alert("XSS")</script>';
    return <div>{msg}</div>;
}
"""
    malicious_result = generate_react_html(malicious_jsx)

    # </script>がエスケープされていることを確認
    # 悪意あるコードの</script>がエスケープされ、元のタグ数と同じになること
    malicious_script_count = malicious_result.count("</script>")
    assert malicious_script_count == normal_script_count

    # エスケープされた形式が存在すること
    assert r"<\/script>" in malicious_result


def test_script_tag_case_insensitive_escape():
    """大文字小文字両方の</SCRIPT>タグがエスケープされることをテスト。"""
    jsx_code = """
function App() {
    const a = '</script>';
    const b = '</SCRIPT>';
    return <div>Test</div>;
}
"""
    result = generate_react_html(jsx_code)

    # 両方エスケープされていること
    assert r"<\/script>" in result
    assert r"<\/SCRIPT>" in result
