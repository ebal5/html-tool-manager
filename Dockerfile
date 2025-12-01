# 1. ベースイメージとしてuv公式イメージを選択
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 2. 環境変数を設定
ENV APP_HOME=/app
WORKDIR $APP_HOME

# 3. 非rootユーザーを作成
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# 4. 依存関係ファイルをコピーしてインストール（キャッシュ効率化）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 5. ソースコードをコピーしてプロジェクトをインストール
COPY ./src ./src
RUN uv sync --frozen --no-dev

# 6. 残りのファイルをコピー
COPY ./static ./static
COPY ./templates ./templates

# 7. OSパッケージをアップデート（セキュリティ修正）
# NOTE: ビルドキャッシュ効率のため、アプリケーション層の後に配置
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*

# 8. ファイルの所有権を変更し、非rootユーザーに切り替え
RUN chown -R appuser:appgroup $APP_HOME
USER appuser

# 9. ポートを公開
EXPOSE 80

# 10. ヘルスチェック
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# 11. アプリケーションを起動するコマンド
CMD ["uv", "run", "--no-sync", "uvicorn", "html_tool_manager.main:app", "--host", "0.0.0.0", "--port", "80"]
