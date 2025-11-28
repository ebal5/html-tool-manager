---
description: ruffでコードのlint/formatを実行します
allowed-tools: Bash
---

コードのlint/formatを実行してください。

## 実行手順

1. `ruff check --fix .` を実行してlintエラーを自動修正
2. `ruff format .` を実行してコードをフォーマット
3. 修正された箇所があれば報告
4. エラーが残っている場合は、修正方法を提案

## 代替コマンド

poeタスクとして `uv run poe lint` でも実行可能です。
