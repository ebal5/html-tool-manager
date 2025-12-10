"""Code type detection module for automatically identifying React/JSX code."""

import re

from html_tool_manager.models.tool import ToolType


def detect_tool_type(code: str) -> ToolType:
    """コードを解析してツールタイプを自動検出する。

    Detection rules:
    1. HTML ドキュメントパターン（DOCTYPE, <html>, <head>）が見つかれば HTML
    2. React の特徴的なパターン（import React, hooks, JSX構文など）が複数マッチすれば React
    3. デフォルトは HTML

    Args:
        code: ユーザーが貼り付けたコード

    Returns:
        検出されたツールタイプ

    """
    # HTML ドキュメントのパターン
    html_patterns = [
        r"<!DOCTYPE\s+html>",
        r"<html[>\s]",
        r"<head[>\s]",
    ]

    # React の特徴的なパターン
    react_patterns = [
        r"import\s+React",  # React import
        r"from\s+['\"]react['\"]",  # from 'react'
        r"useState|useEffect|useContext|useReducer|useMemo|useCallback",  # React Hooks
        r"ReactDOM\.render|createRoot",  # ReactDOM
        r"<[A-Z]\w+\s+",  # JSX Component (大文字で始まる)
        r"<\w+\s+\w+={",  # JSX props with expressions
        r"function\s+\w+\s*\([^)]*\)\s*{\s*return\s*\(",  # Function component pattern
        r"const\s+\w+\s*=\s*\([^)]*\)\s*=>\s*{",  # Arrow function component
    ]

    # HTML ドキュメントとして完全な場合は HTML
    if any(re.search(pattern, code, re.IGNORECASE) for pattern in html_patterns):
        return ToolType.HTML

    # React パターンが複数マッチする場合は React
    react_matches = sum(1 for pattern in react_patterns if re.search(pattern, code))
    if react_matches >= 2:  # 2つ以上のパターンにマッチ
        return ToolType.REACT

    # デフォルトは HTML
    return ToolType.HTML
