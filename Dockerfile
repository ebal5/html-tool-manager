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

# 7. OSパッケージをアップデート、gosuをインストール（セキュリティ修正）
# gosu: ENTRYPOINTでroot→appuserへの権限降格に使用
# NOTE: ビルドキャッシュ効率のため、アプリケーション層の後に配置
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/* && \
    gosu nobody true

# 8. ファイルの所有権を変更
RUN chown -R appuser:appgroup $APP_HOME

# 9. エントリーポイントスクリプトをコピー
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 10. ポートを公開
EXPOSE 80

# 11. ヘルスチェック
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# 12. エントリーポイントとコマンドを設定
# ENTRYPOINTはrootで実行され、ボリュームの権限を修正後にappuserとしてCMDを実行
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uv", "run", "--no-sync", "uvicorn", "html_tool_manager.main:app", "--host", "0.0.0.0", "--port", "80"]
