# HTMLツールマネージャー

[![CI](https://github.com/ebal5/html-tool-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/ebal5/html-tool-manager/actions/workflows/ci.yml)
[![GitHub Container Registry](https://img.shields.io/badge/Container-ghcr.io-blue?logo=github)](https://github.com/ebal5/html-tool-manager/pkgs/container/html-tool-manager)

単一ページのHTML/JSツールを管理・ホストするためのシンプルなWebアプリケーションです。このプロジェクトは、人間とAIアシスタントの共同作業によって開発されました。

## 主な機能

- **ツール管理:** Webインターフェースを介したツールの作成、閲覧、更新、削除（CRUD）。
- **React/JSX対応:** Claude Artifacts や Gemini Canvas で生成された React コードを直接管理。
  - **自動検出:** コードを貼り付けるだけで React/HTML を自動判定。
  - **自動変換:** import/export 文を自動変換しブラウザで実行可能に。
  - **Tailwind CSS:** React コードには自動的に Tailwind CDN を読み込み。
- **コンテンツ作成:** HTML/React コンテンツを直接貼り付けて新しいツールを作成。
- **ライブホスティング:** 「Use」ボタンでツールを`iframe`内にレンダリングして使用。
- **高度な検索:** 強力な検索バーは以下をサポートします:
  - 名前、説明、タグを横断した全文検索。
  - プレフィックスベースの検索 (例: `name:my-tool`, `desc:calculator`, `tag:json`)。
  - ダブルクォートによるフレーズ検索 (例: `name:"My Awesome Tool"`)。
- **ソート:** 関連度、名前、更新日でツール一覧を並び替え。
- **モダンなUI:** [Pico.css](https://picocss.com/) で構築された、クリーンでレスポンシブなユーザーインターフェース。
- **コンテナ化:** `Dockerfile` が含まれており、簡単なコンテナ化とデプロイが可能。

## 技術スタック

- **バックエンド:** Python 3.12+ と [FastAPI](https://fastapi.tiangolo.com/)
- **データベース:** [SQLite](https://www.sqlite.org/index.html) (全文検索のためのFTS5拡張を含む)
- **ORM:** [SQLModel](https://sqlmodel.tiangolo.com/)
- **フロントエンド:** [Pico.css](https://picocss.com/) でスタイリングされた素のHTML, CSS, JavaScript
- **Python環境:** `uv` によるパッケージと仮想環境の管理
- **タスクランナー:** `poethepoet` による開発タスクの実行

## セットアップ方法

### 事前準備

- Python 3.12+
- `uv` (`pip`, `pipx`, またはシステムのパッケージマネージャーでインストール可能)

### 開発環境

1.  **リポジトリをクローン:**
    ```bash
    git clone <リポジトリURL>
    cd html_tool_manager
    ```

2.  **仮想環境の作成と依存関係のインストール:**
    `uv` が `.venv` ディレクトリを作成し、必要なパッケージをすべてインストールします。
    ```bash
    uv sync
    ```

3.  **開発サーバーの実行:**
    このコマンドは `poethepoet` を使い、ホットリロードを有効にして `uvicorn` を実行します。
    ```bash
    uv run poe dev
    ```
    アプリケーションは `http://127.0.0.1:8000` で利用可能になります。

4.  **テストの実行:**
    ```bash
    uv run pytest
    ```

5.  **コード品質チェック:**
    ```bash
    # Python lint/format
    uv run poe lint

    # フロントエンド lint/format (Biome)
    npx @biomejs/biome check static/js/

    # 型チェック (mypy)
    uv run poe typecheck

    # 型チェック 実験的 (ty - Astral製、pre-alpha)
    uv run poe typecheck-experimental
    ```

    > **Note:** [ty](https://docs.astral.sh/ty/) は Astral (ruff, uv の開発元) が開発中の高速型チェッカーです。
    > 現在 pre-alpha のため参考用として導入しています。本番の型チェックには mypy を使用してください。

### Docker

#### GitHub Container Registry からの取得（推奨）

プリビルドされたDockerイメージがGitHub Container Registryで利用可能です。

```bash
# 最新バージョンを取得
docker pull ghcr.io/ebal5/html-tool-manager:latest

# 特定バージョンを取得
docker pull ghcr.io/ebal5/html-tool-manager:0.2.0
```

**コンテナの実行:**

```bash
docker run -d -p 8080:80 \
  -v html-tool-manager-data:/data \
  --name html-tool-manager-app \
  ghcr.io/ebal5/html-tool-manager:latest
```

アプリケーションは `http://127.0.0.1:8080` で利用可能になります。

#### ローカルでビルド

1.  **Dockerイメージのビルド:**
    ```bash
    docker build -t html-tool-manager:local .
    ```

2.  **Dockerコンテナの実行:**
    ```bash
    docker run -d -p 8080:80 \
      -v html-tool-manager-data:/data \
      --name html-tool-manager-app \
      html-tool-manager:local
    ```

**ボリューム説明:**
- `html-tool-manager-data`: データベースファイル (`/data/tools.db`) とツールファイル (`/data/tools/`) の永続化

**データディレクトリ構成:**
```
/data/
├── tools.db        # SQLiteデータベース
└── tools/          # ツールHTMLファイル
```

> **Security:** エントリーポイントはボリューム権限修正のため一時的にrootで実行されますが、
> 即座に`gosu`で非rootユーザー（UID 1000）に降格します。アプリケーション自体はroot権限で実行されません。

## セキュリティ

このプロジェクトでは、複数のレイヤーでセキュリティスキャンを実施しています：

- **Pythonコード**: bandit によるコード脆弱性スキャン
- **Python依存関係**: pip-audit による既知の脆弱性チェック
- **Dockerイメージ**: Trivy によるOSパッケージとアプリケーション依存関係のスキャン

詳細は [セキュリティスキャンドキュメント](docs/security-scanning.md) を参照してください。

## データベースマイグレーション

新しいバージョンにアップグレードする際、データベーススキーマの変更が必要な場合があります。

### v0.1.6 → v0.2.0: React 対応

v0.2.0 で React/JSX 対応が追加されました。既存のデータベースがある場合は、以下のマイグレーションスクリプトを実行してください：

```bash
# 開発環境
python scripts/migrate_add_tool_type.py

# Docker環境
docker exec -it html-tool-manager-app python scripts/migrate_add_tool_type.py
```

**処理内容:**
- `tool` テーブルに `tool_type` カラムを追加
- 既存のツールはすべて `html` タイプに設定

**ロールバック:**
スキーマ変更をロールバックする場合は、データベースのバックアップから復元するか、手動で以下のSQLを実行してください：

```sql
-- SQLite ではカラム削除に対応していないため、テーブルを再作成する必要があります
-- バックアップを取ってから実行してください
```

> **Note:** 新規インストールの場合、マイグレーションは不要です。アプリケーション起動時に自動的に最新のスキーマでデータベースが作成されます。
