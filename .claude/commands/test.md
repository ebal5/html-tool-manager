---
description: pytestでテストを実行し、結果を報告します
allowed-tools: Bash
argument-hint: [テスト対象パス（オプション）]
---

pytestでテストを実行してください。

## 実行手順

1. `uv run pytest $ARGUMENTS -v` を実行（引数がなければ全テスト）
2. テスト結果を分析
3. 失敗したテストがあれば、原因を説明し修正方法を提案

## 使用例

- `/test` - 全テスト実行
- `/test tests/test_search.py` - 特定のファイルのみ
- `/test -k "test_name"` - 特定のテストのみ

## 代替コマンド

poeタスクとして `uv run poe test` でも実行可能です。
