---
description: HTML Tool Managerの開発サーバーを起動します
allowed-tools: Bash
---

開発サーバーを起動してください。

## 実行手順

1. `uv run poe dev` を実行
2. サーバーが起動したら以下を伝える：
   - アクセスURL: http://localhost:8000
   - API docs: http://localhost:8000/docs
3. 終了方法（Ctrl+C）を案内

## 注意事項

- ホットリロードが有効なので、コード変更は自動的に反映されます
- DBファイル（sql_app.db）が存在しない場合は自動作成されます
