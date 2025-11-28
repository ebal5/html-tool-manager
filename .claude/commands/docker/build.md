---
description: HTML Tool ManagerのDockerイメージをビルドします
allowed-tools: Bash
argument-hint: [タグ名（デフォルト: html-tool-manager:latest）]
---

Dockerイメージをビルドしてください。

## 実行手順

1. タグ名を決定：
   - 引数が指定されていればそれを使用
   - なければ `html-tool-manager:latest` を使用
2. `docker build -t <タグ名> .` を実行
3. ビルド結果を報告：
   - 成功した場合: イメージサイズを含めて報告
   - 失敗した場合: エラー内容と修正方法を提案

## 使用例

- `/docker:build` - デフォルトタグでビルド
- `/docker:build html-tool-manager:0.2.0` - バージョン指定

## 注意事項

- ビルドにはDockerデーモンが起動している必要があります
- uvの公式イメージをベースにしています
