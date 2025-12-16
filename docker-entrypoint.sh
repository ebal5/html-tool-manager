#!/usr/bin/env sh
set -e

# データディレクトリの権限を修正（ボリュームマウント時にrootになる問題に対応）

# /dataディレクトリ（存在しない場合は作成）
if [ ! -d "/data" ]; then
    mkdir -p /data/tools
fi

# 所有権がrootの場合のみchownを実行（起動高速化）
if [ "$(stat -c %u /data 2>/dev/null)" = "0" ]; then
    chown -R appuser:appgroup /data || echo "Warning: Could not change ownership of /data"
fi

# appuserとしてコマンドを実行
exec gosu appuser "$@"
