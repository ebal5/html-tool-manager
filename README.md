# HTMLツールマネージャー

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
    uv pip install -e .[dev]
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

### Docker

1.  **Dockerイメージのビルド:**
    ```bash
    docker build -t html-tool-manager .
    ```

2.  **Dockerコンテナの実行:**
    このコマンドは、コンテナのポート80をホストのポート8000にマッピングします。また、`html-tool-manager-data` と `html-tool-manager-db` という名前のボリュームを作成し、アップロードされたツールファイルとSQLiteデータベースをそれぞれ永続化させます。
    ```bash
    docker run -d -p 8000:80 -v html-tool-manager-data:/app/static/tools -v html-tool-manager-db:/app --name html-tool-manager-app html-tool-manager
    ```
    - アプリケーションは `http://127.0.0.1:8000` で利用可能になります。
    - データベースファイル (`sql_app.db`) は `html-tool-manager-db` ボリュームに永続化されます。
    - アップロードされたツールは `html-tool_manager-data` ボリュームに永続化されます。
