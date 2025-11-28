# 1. ベースイメージとしてuv公式イメージを選択
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 2. 環境変数を設定
ENV APP_HOME=/app
WORKDIR $APP_HOME

# 3. 依存関係ファイルをコピーしてインストール（キャッシュ効率化）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 4. ソースコードをコピーしてプロジェクトをインストール
COPY ./src ./src
RUN uv sync --frozen --no-dev

# 5. 残りのファイルをコピー
COPY ./static ./static
COPY ./templates ./templates

# 6. ヘルスチェック
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# 7. アプリケーションを起動するコマンド
CMD ["uv", "run", "uvicorn", "html_tool_manager.main:app", "--host", "0.0.0.0", "--port", "80"]