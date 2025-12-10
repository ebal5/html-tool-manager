"""React template generation module for wrapping JSX code in executable HTML."""


def generate_react_html(jsx_code: str) -> str:
    """JSX コードを実行可能な HTML でラップする。

    React 18 と ReactDOM を CDN から読み込み、Babel Standalone を使って
    JSX をブラウザ上でトランスパイルします。

    Args:
        jsx_code: ユーザーが貼り付けた JSX コード

    Returns:
        完全な HTML ドキュメント

    """
    # import/export 文を変換
    transformed_code = _transform_imports_exports(jsx_code)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>React Tool</title>
    <!-- Tailwind CSS (SRI なし: CORS 非対応のため) -->
    <script src="https://cdn.tailwindcss.com/3.4.1"></script>
    <!-- React 18 & ReactDOM -->
    <script
        crossorigin
        src="https://unpkg.com/react@18.2.0/umd/react.production.min.js"
        integrity="sha384-tMH8h3BGESGckSAVGZ82T9n90ztNXxvdwvdM6UoR56cYcf+0iGXBliJ29D+wZ/x8"></script>
    <script
        crossorigin
        src="https://unpkg.com/react-dom@18.2.0/umd/react-dom.production.min.js"
        integrity="sha384-bm7MnzvK++ykSwVJ2tynSE5TRdN+xL418osEVF2DE/L/gfWHj91J2Sphe582B1Bh"></script>
    <!-- Babel Standalone for JSX transformation -->
    <script
        src="https://unpkg.com/@babel/standalone@7.23.5/babel.min.js"
        integrity="sha384-1qlE7MZPM2pHD/pBZCU/yB8UCP52RYL8bge/qNdfNBCWToySp8/M+JL2waXU4hjJ"
        crossorigin="anonymous"></script>
    <style>
        body {{
            margin: 0;
            font-family: system-ui, -apple-system, sans-serif;
        }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel" data-type="module">
        // React を UMD グローバルから取得
        const React = window.React;
        const {{
            // 基本 hooks
            useState, useEffect, useContext, useReducer,
            useCallback, useMemo, useRef,
            // 追加 hooks
            useLayoutEffect, useImperativeHandle, useDebugValue,
            // React 18 hooks
            useTransition, useDeferredValue, useId, useSyncExternalStore, useInsertionEffect
        }} = React;
        const ReactDOM = window.ReactDOM;

{transformed_code}

        // コンポーネントをレンダリング
        const rootElement = document.getElementById('root');
        const root = ReactDOM.createRoot(rootElement);
        root.render(React.createElement(App));
    </script>
</body>
</html>"""


def _transform_imports_exports(code: str) -> str:
    """import/export 文をブラウザ対応の形式に変換する。

    Args:
        code: 元の JSX コード

    Returns:
        変換後のコード

    """
    import re

    # import 文を削除（React hooks は上で定義済み）
    code = re.sub(r"^import\s+.*?from\s+['\"]react['\"];?\s*$", "", code, flags=re.MULTILINE)
    code = re.sub(r"^import\s+.*?from\s+['\"]react-dom['\"];?\s*$", "", code, flags=re.MULTILINE)

    # export default function Name を App に変更
    code = re.sub(
        r"export\s+default\s+function\s+(\w+)",
        r"function App",
        code,
    )

    # export default const Name = () => {} を const App = () => {} に変更
    code = re.sub(
        r"export\s+default\s+(const|let|var)\s+\w+\s*=",
        r"const App =",
        code,
    )

    # 単独の export default Name; を削除（関数宣言は別の場所にある想定）
    # この場合、元の関数名がそのまま使われるので App へのリネームは別途必要
    code = re.sub(r"^export\s+default\s+\w+;?\s*$", "", code, flags=re.MULTILINE)

    # 他の export 文も削除
    code = re.sub(r"^export\s+", "", code, flags=re.MULTILINE)

    return code
