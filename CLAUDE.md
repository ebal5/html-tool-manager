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

#### Python (ruff)

```bash
# lint修正とフォーマット
ruff check --fix && ruff format

# CI前の確認（両方パスすることを確認）
ruff check . && ruff format --check .
```

**重要**: `ruff check --fix`と`ruff format`は必ずセットで実行する。
checkでインポート順序（I001）を修正しても、formatを実行しないと括弧の配置などが更新されずCIで失敗する。

#### フロントエンド (Biome)

```bash
# lint/format チェック
npx @biomejs/biome check static/js/

# 自動修正
npx @biomejs/biome check --write static/js/
```

### コミット前チェック

- テスト実行: `uv run pytest`
- Python lint: `ruff check . && ruff format --check .`
- フロント lint: `npx @biomejs/biome check static/js/`
- 型チェック: `uv run mypy src/`

### プッシュ前チェック（必須）

**重要**: `git push` を実行する前に、以下のチェックを**必ず**実行すること。

```bash
# 1. Lint/Format（修正＋確認）
uv run ruff check --fix . && uv run ruff format .
uv run ruff check . && uv run ruff format --check .

# 2. ユニットテスト（E2Eは除外）
uv run pytest -m "not e2e" -x

# 3. 型チェック（オプションだが推奨）
uv run mypy src/
```

これらのチェックがすべてパスしてからプッシュすること。CIの無駄な実行を防ぎ、レビューの手間を減らすため。

## API概要

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | /api/tools/ | ツール作成 |
| GET | /api/tools/ | 一覧・検索（?q=, ?sort=） |
| GET | /api/tools/{id} | 詳細取得 |
| PUT | /api/tools/{id} | 更新 |
| DELETE | /api/tools/{id} | 削除 |
| POST | /api/tools/{id}/fork | ツール複製（フォーク） |
| GET | /api/tools/tags/suggest | タグ候補取得（?q=） |
| POST | /api/tools/export | エクスポート |
| POST | /api/tools/import | インポート |

### フォークAPI

既存のツールを複製して新しいツールを作成する。

**エンドポイント**: `POST /api/tools/{id}/fork`

**リクエストボディ**:
```json
{
  "name": "新しいツール名"  // 省略または空の場合は「元の名前 (Fork)」
}
```

**レスポンス**: 201 Created + 新しいツールの`ToolRead`

**エラー**:
- 404: 元ツールが存在しない、またはファイルが見つからない
- 400: 名前が長すぎる（100文字超）、または無効なファイルパス

## 検索クエリ構文

- `name:xxx` - 名前プレフィックス検索
- `desc:xxx` - 説明プレフィックス検索
- `tag:xxx` - タグ部分一致検索
- `"phrase"` - フレーズ検索

## スナップショット機能

ツールの変更履歴を自動保存し、過去のバージョンに復元できる機能。

### スナップショットAPI

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | /api/tools/{id}/snapshots | スナップショット一覧 |
| POST | /api/tools/{id}/snapshots | 手動スナップショット作成 |
| GET | /api/tools/{id}/snapshots/{snapshot_id} | 詳細取得（コンテンツ含む） |
| DELETE | /api/tools/{id}/snapshots/{snapshot_id} | 削除 |
| POST | /api/tools/{id}/snapshots/{snapshot_id}/restore | 復元 |
| GET | /api/tools/{id}/snapshots/{snapshot_id}/diff | 差分取得 |

### 設定

- 保持上限: 20件/ツール（`MAX_SNAPSHOTS_PER_TOOL` in `models/snapshot.py`）
- 自動保存: ツール更新時に内容が変更された場合のみ

## 注意事項

### データベースマイグレーション

新しいテーブル（`tool_snapshot`等）はアプリケーション起動時に自動作成されます。

**既存環境のアップグレード手順:**
1. アプリケーションを停止
2. 新しいコードをデプロイ
3. アプリケーションを起動（テーブルが自動作成される）

**注意**: SQLModelは自動的に存在しないテーブルを作成しますが、既存テーブルのスキーマ変更は行いません。カラム追加等が必要な場合は手動でALTER文を実行してください。

### バリデーション定数の同期

バリデーションルールは以下の2箇所で定義されており、**変更時は両方を更新すること**：

- Python: `src/html_tool_manager/models/tool.py` (NAME_MAX_LENGTH等)
- JavaScript: `static/js/validation.js` (ValidationRules)
