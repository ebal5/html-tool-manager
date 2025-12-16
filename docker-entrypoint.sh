#!/usr/bin/env sh
set -e

# データディレクトリの権限を修正（ボリュームマウント時にrootになる問題に対応）

# ツールファイル用ディレクトリ（存在しない場合は作成）
if [ ! -d "/app/static/tools" ]; then
    mkdir -p /app/static/tools
fi

# 所有権がrootの場合のみchownを実行（起動高速化）
if [ "$(stat -c %u /app/static/tools 2>/dev/null)" = "0" ]; then
    chown -R appuser:appgroup /app/static/tools || echo "Warning: Could not change ownership of /app/static/tools"
fi

# DBファイルの処理（存在チェックと所有権設定を統合）
if [ -f "/app/tools.db" ]; then
    chown appuser:appgroup /app/tools.db || echo "Warning: Could not change ownership of /app/tools.db"
else
    touch /app/tools.db || echo "Warning: Could not create /app/tools.db"
    chown appuser:appgroup /app/tools.db || echo "Warning: Could not change ownership of /app/tools.db"
fi

# appuserとしてコマンドを実行
exec gosu appuser "$@"
