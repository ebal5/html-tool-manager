# HTML Tool Manager

## プロジェクト概要

- 目的：HTML/JSツールを管理・ホストするWebアプリケーション
- 技術スタック：FastAPI, SQLite (FTS5), SQLModel, Pico.css, Jinja2
- パッケージ管理：uv

## アーキテクチャ

```
src/html_tool_manager/
├── main.py              # FastAPIアプリ、ルート定義
├── api/tools.py         # CRUD API、検索、エクスポート/インポート
├── api/query_parser.py  # 検索クエリパーサー
├── models/tool.py       # SQLModelデータモデル
├── repositories/        # データアクセス層
└── core/db.py           # DB初期化
```

## 開発ガイドライン

### 環境セットアップ

```bash
uv sync
```

### 開発サーバー起動

```bash
uv run poe dev
```

### テスト実行

```bash
uv run pytest
```

### コードスタイル

```bash
ruff check --fix && ruff format
```

### コミット前チェック

- テスト実行
- lint/format確認

## API概要

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
