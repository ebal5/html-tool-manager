# HTMLツールマネージャー

[![CI](https://github.com/ebal5/html-tool-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/ebal5/html-tool-manager/actions/workflows/ci.yml)
[![GitHub Container Registry](https://img.shields.io/badge/Container-ghcr.io-blue?logo=github)](https://github.com/ebal5/html-tool-manager/pkgs/container/html-tool-manager)

単一ページのHTML/JSツールを管理・ホストするためのシンプルなWebアプリケーションです。このプロジェクトは、人間とAIアシスタントの共同作業によって開発されました。

## 主な機能

- **ツール管理:** Webインターフェースを介したツールの作成、閲覧、更新、削除（CRUD）。
- **コンテンツ作成:** HTMLコンテンツを直接貼り付けて新しいツールを作成。
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
docker pull ghcr.io/ebal5/html-tool-manager:0.1.0
```

**コンテナの実行:**

```bash
docker run -d -p 8888:80 \
  -v html-tool-manager-data:/app/static/tools \
  -v html-tool-manager-db:/app \
  --name html-tool-manager-app \
  ghcr.io/ebal5/html-tool-manager:latest
```

アプリケーションは `http://127.0.0.1:8888` で利用可能になります。

#### ローカルでビルド

1.  **Dockerイメージのビルド:**
    ```bash
    docker build -t html-tool-manager:local .
    ```

2.  **Dockerコンテナの実行:**
    ```bash
    docker run -d -p 8888:80 \
      -v html-tool-manager-data:/app/static/tools \
      -v html-tool-manager-db:/app \
      --name html-tool-manager-app \
      html-tool-manager:local
    ```

**ボリューム説明:**
- `html-tool-manager-db`: データベースファイル (`sql_app.db`) の永続化
- `html-tool-manager-data`: アップロードされたツールの永続化

## セキュリティ

このプロジェクトでは、複数のレイヤーでセキュリティスキャンを実施しています：

- **Pythonコード**: bandit によるコード脆弱性スキャン
- **Python依存関係**: pip-audit による既知の脆弱性チェック
- **Dockerイメージ**: Trivy によるOSパッケージとアプリケーション依存関係のスキャン

詳細は [セキュリティスキャンドキュメント](docs/security-scanning.md) を参照してください。
