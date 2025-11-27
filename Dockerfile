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
COPY ./static ./static # フロントエンドファイルをコピー
COPY ./templates ./templates # テンプレートファイルをコピー

# 6. アプリケーションを起動するコマンド
#    FastAPIアプリケーションが `src.html_tool_manager.main` の `app` オブジェクトであると仮定
#    uvicorn は `src` ディレクトリがPYTHONPATHに含まれていなくても、モジュールパスとして認識できるように `src.` をつけて呼び出す
CMD ["uvicorn", "src.html_tool_manager.main:app", "--host", "0.0.0.0", "--port", "80"]