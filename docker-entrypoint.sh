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

# 大規模ボリュームでの起動最適化
# CHOWN_STRATEGY: "skip", "top-level", "recursive" (default: "auto")
# - skip: chownを完全にスキップ
# - top-level: トップレベルのみchown（高速）
# - recursive: 再帰的にchown（確実だが遅い）
# - auto: マーカーファイル + rootチェックで自動判定
CHOWN_STRATEGY="${CHOWN_STRATEGY:-auto}"
CHOWN_MARKER="/data/.chown_done"

case "$CHOWN_STRATEGY" in
    skip)
        echo "Skipping chown (CHOWN_STRATEGY=skip)"
        ;;
    top-level)
        echo "Applying top-level chown only..."
        chown appuser:appgroup /data || {
            echo "Error: Failed to change ownership of /data"
            exit 1
        }
        # toolsディレクトリが存在する場合のみchown
        if [ -d "/data/tools" ]; then
            chown appuser:appgroup /data/tools
        fi
        ;;
    recursive)
        echo "Applying recursive chown..."
        chown -R appuser:appgroup /data || {
            echo "Error: Failed to change ownership of /data"
            exit 1
        }
        ;;
    auto|*)
        # マーカーファイルが存在し、所有権も正しい場合はスキップ
        if [ -f "$CHOWN_MARKER" ] && [ "$(stat -c %u /data)" != "0" ]; then
            echo "Skipping chown (already configured)"
        # 所有権がrootの場合、またはマーカーがない場合は実行
        elif [ "$(stat -c %u /data)" = "0" ] || [ ! -f "$CHOWN_MARKER" ]; then
            echo "Applying recursive chown (first run or root-owned volume)..."
            chown -R appuser:appgroup /data || {
                echo "Error: Failed to change ownership of /data"
                exit 1
            }
            # マーカーファイルを作成（次回起動時にスキップ）
            touch "$CHOWN_MARKER"
            chown appuser:appgroup "$CHOWN_MARKER"
        fi
        ;;
esac

# appuserとしてコマンドを実行
exec gosu appuser "$@"
