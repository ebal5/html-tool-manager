# 1. ベースイメージとして公式のPythonイメージを選択
FROM python:3.12-slim

# 2. uvをインストール
RUN pip install uv

# 3. 環境変数を設定
ENV APP_HOME=/app
WORKDIR $APP_HOME

# 4. 依存関係をインストール
#    本番環境では開発依存関係は不要なので、[dev]は含めない
COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

# 5. アプリケーションのソースコードをコピー
COPY ./src ./src
COPY ./static ./static
COPY ./templates ./templates

# 6. PYTHONPATHを設定して、srcディレクトリをインポートパスに追加
ENV PYTHONPATH=/app/src

# 7. アプリケーションを起動するコマンド
CMD ["uvicorn", "html_tool_manager.main:app", "--host", "0.0.0.0", "--port", "80"]