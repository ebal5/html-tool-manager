#!/usr/bin/env sh
set -e

# データディレクトリの権限を修正（ボリュームマウント時にrootになる問題に対応）

# ツールファイル用ディレクトリ（存在しない場合は作成）
if [ ! -d "/app/static/tools" ]; then
    mkdir -p /app/static/tools
fi
chown -R appuser:appgroup /app/static/tools || echo "Warning: Could not change ownership of /app/static/tools"

# DBファイル（存在する場合）
if [ -f "/app/tools.db" ]; then
    chown appuser:appgroup /app/tools.db || echo "Warning: Could not change ownership of /app/tools.db"
fi

# DBファイルが存在しない場合、親ディレクトリに書き込み権限が必要
# /app自体がマウントされている場合に備える
if [ -w "/app" ] && [ ! -f "/app/tools.db" ]; then
    # /appがrootで書き込み可能なら、appuserが書き込めるようにする
    # ただし、アプリケーションファイルの所有権は変更しない
    touch /app/tools.db
    chown appuser:appgroup /app/tools.db || echo "Warning: Could not change ownership of /app/tools.db"
fi

# appuserとしてコマンドを実行
exec gosu appuser "$@"
