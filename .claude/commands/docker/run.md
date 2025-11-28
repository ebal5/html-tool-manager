---
description: HTML Tool ManagerのDockerコンテナを起動します
allowed-tools: Bash
argument-hint: [ポート番号（デフォルト: 8080）]
---

Dockerコンテナを起動してください。

## 実行手順

1. ポートを決定：
   - 引数が指定されていればそれを使用
   - なければ `8080` を使用
2. 既存のコンテナが存在する場合は削除
3. 以下のコマンドを実行：
   ```bash
   docker run -d -p <ポート>:80 \
     -v html-tool-manager-data:/app/static/tools \
     -v html-tool-manager-db:/app \
     --name html-tool-manager \
     html-tool-manager:latest
   ```
4. http://localhost:<ポート> でアクセス可能なことを伝える

## コンテナ管理コマンド

- 停止: `docker stop html-tool-manager`
- 削除: `docker rm html-tool-manager`
- ログ確認: `docker logs html-tool-manager`

## 注意事項

- データは永続化ボリュームに保存されます
- ポート競合がある場合は別のポートを指定してください
