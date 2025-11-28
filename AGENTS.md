# AI Agent Collaboration Guide

このドキュメントはAIエージェント向けの開発ガイドラインです。

## 開発時の重要事項

### アーキテクチャ理解

- クリーンアーキテクチャ風：API層 → リポジトリ層 → モデル層
- 全文検索はSQLite FTS5を使用
- テンプレートエンジン：Jinja2
- CSSフレームワーク：Pico.css（クラスレス）

### コード変更時の注意点

- 日本語コメント/docstring推奨
- SQLModel使用時はPydanticとSQLAlchemyの両方の特性を考慮
- テストはインメモリSQLiteで実行（`conftest.py`参照）

### Lint/Format ベストプラクティス

#### Python (ruff)

- **checkとformatは必ずセット**: `ruff check --fix`後に`ruff format`も実行
- **push前に確認**: `ruff check . && ruff format --check .` で両方パスすることを確認
- checkでインポート順序を修正しても、formatで括弧配置等が変わることがある

#### フロントエンド (Biome)

- **グローバル無効化よりインライン無効化を優先**
- 特定箇所のみ無効化する場合は `biome-ignore` コメントを使用:
  ```javascript
  // biome-ignore lint/correctness/noUnusedVariables: HTMLから呼び出される関数
  function myFunction() { ... }
  ```
- HTMLテンプレートから呼び出される関数は「未使用」と誤検知されるのでignoreが必要

#### CI前の検証

- ローカルで全チェックがパスするまでpushしない
- CIと同じコマンドをローカルで実行して確認

### テスト

- `tests/conftest.py`でDB fixtureを提供
- 新機能にはテストを追加すること
- テスト実行：`uv run pytest`

### 禁止事項

- セキュリティ：パストラバーサル、XSS脆弱性の導入禁止
- 本番DBファイル（`sql_app.db`）の直接操作禁止
- `.env`ファイルや認証情報のコミット禁止

## 関連ドキュメント

- `README.md` - セットアップ手順
- `DESIGN.md` - UI/UXガイドライン
- `CLAUDE.md` - プロジェクト概要と開発ガイドライン
