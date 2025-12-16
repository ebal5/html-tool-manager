#!/usr/bin/env sh
set -e

# データディレクトリの権限を修正（ボリュームマウント時にrootになる問題に対応）

# /dataディレクトリ（存在しない場合は作成）
if [ ! -d "/data" ]; then
    mkdir -p /data/tools
fi

# セキュリティ: /dataがシンボリックリンクでないことを確認
if [ -L "/data" ]; then
    echo "Error: /data must be a directory, not a symlink"
    exit 1
fi

# 所有権がrootの場合のみchownを実行（起動高速化）
if [ "$(stat -c %u /data)" = "0" ]; then
    chown -R appuser:appgroup /data || {
        echo "Error: Failed to change ownership of /data"
        exit 1
    }
fi

# appuserとしてコマンドを実行
exec gosu appuser "$@"
