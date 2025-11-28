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
