---
name: html-tool-explorer
description: HTML Tool Managerのコードベースを探索し、アーキテクチャ、API、データモデルを分析します。プロジェクト構造の理解や機能追加の調査時に使用してください。
allowed-tools: Read, Grep, Glob
---

# HTML Tool Manager コードベース探索

このスキルはHTML Tool Managerプロジェクトの構造理解と調査を支援します。

## プロジェクト構造

```
src/html_tool_manager/
├── main.py              # FastAPIアプリケーション、ルート定義
├── api/
│   ├── tools.py         # CRUD API実装（POST/GET/PUT/DELETE）
│   └── query_parser.py  # 検索クエリパーサー
├── models/
│   └── tool.py          # SQLModelデータモデル（Tool, ToolCreate, ToolRead）
├── repositories/
│   └── tool_repository.py  # データアクセス層（CRUD操作、FTS検索）
└── core/
    └── db.py            # DB初期化、FTS5セットアップ

templates/               # Jinja2テンプレート
├── index.html           # ツール一覧ページ
├── create.html          # ツール作成フォーム
├── edit.html            # ツール編集フォーム
└── tool_viewer.html     # ツール表示（iframe）

tests/                   # テストスイート
├── conftest.py          # pytest fixture（インメモリDB）
├── test_search.py       # 検索機能テスト
└── test_import_export.py  # エクスポート/インポートテスト
```

## 技術スタック

- **フレームワーク**: FastAPI
- **ORM**: SQLModel（Pydantic + SQLAlchemy）
- **データベース**: SQLite + FTS5（全文検索）
- **テンプレート**: Jinja2
- **CSS**: Pico.css（クラスレス）
- **パッケージ管理**: uv
- **タスクランナー**: poethepoet

## API仕様

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | /api/tools/ | ツール作成 |
| GET | /api/tools/ | 一覧・検索（?q=, ?sort=） |
| GET | /api/tools/{id} | 詳細取得 |
| PUT | /api/tools/{id} | 更新 |
| DELETE | /api/tools/{id} | 削除 |
| POST | /api/tools/export | エクスポート |
| POST | /api/tools/import | インポート |

## 検索クエリ構文

- `name:xxx` - 名前プレフィックス検索
- `desc:xxx` - 説明プレフィックス検索
- `tag:xxx` - タグ部分一致検索
- `"phrase"` - フレーズ検索

## 探索時の注意点

1. **SQLModelの特性**: PydanticとSQLAlchemyの両方の機能を持つ
2. **FTS5仮想テーブル**: tool_ftsテーブルはToolテーブルと同期
3. **トリガー**: INSERT/UPDATE/DELETEでFTSテーブルが自動更新
4. **ファイル管理**: HTMLは `static/tools/{uuid}/index.html` に保存

## 参考ドキュメント

詳細は以下のファイルを参照:
- `CLAUDE.md` - 開発ガイドライン
- `DESIGN.md` - UI/UXガイドライン
- `AGENTS.md` - AI向けガイドライン
