---
description: リリース作業を自動化（チェック、テスト、Docker確認、タグ作成）
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git fetch:*), Bash(git describe:*), Bash(git log:*), Bash(git add:*), Bash(git commit:*), Bash(git tag:*), Bash(git push:*), Bash(uv run pytest:*), Bash(ruff:*), Bash(uv run bandit:*), Bash(npx @biomejs/biome:*), Bash(docker build:*), Bash(docker run:*), Bash(docker stop:*), Bash(docker rm:*), Bash(docker rmi:*), Bash(curl:*), Bash(sleep:*), Edit, Read
argument-hint: [version: patch|minor|major|x.y.z]
---

リリース作業を実行してください。

## 引数の解釈

- 引数なし: 変更内容を分析してバージョンを自動提案
- `patch`: パッチバージョンを上げる（例: 0.1.1 -> 0.1.2）
- `minor`: マイナーバージョンを上げる（例: 0.1.1 -> 0.2.0）
- `major`: メジャーバージョンを上げる（例: 0.1.1 -> 1.0.0）
- `x.y.z`: 指定されたバージョンを使用

## Phase 1: プリフライトチェック

以下を順番に確認し、すべてパスしたら次のフェーズへ進む。問題があれば中断して報告。

1. **未コミット変更の確認**
   ```bash
   git status --porcelain
   ```
   - 出力がある場合: 変更ファイルを表示し、コミットまたはstashを促して中断

2. **ブランチ確認**
   ```bash
   git branch --show-current
   ```
   - `main` でない場合: 現在のブランチを表示し、mainへの切り替えを促して中断

3. **リモートとの同期確認**
   ```bash
   git fetch origin
   git status
   ```
   - 「Your branch is behind」または「Your branch is ahead」の場合: pull/pushを促して中断

## Phase 2: 品質チェック

すべてのチェックを実行し、結果をサマリー表示。失敗があれば中断。

1. **テスト実行**
   ```bash
   uv run pytest -v
   ```

2. **Lintチェック**
   ```bash
   ruff check . && ruff format --check .
   ```

3. **セキュリティスキャン**
   ```bash
   uv run bandit -r src/
   ```
   - HIGH/MEDIUM の問題があれば中断
   - LOW のみなら警告として続行可

4. **フロントエンドLintチェック**
   ```bash
   npx @biomejs/biome check static/js/
   ```
   - エラーがあれば中断
   - 修正が必要な場合: `npx @biomejs/biome check --write static/js/`

## Phase 3: Docker動作確認

1. **既存コンテナの確認とクリーンアップ**
   ```bash
   docker ps -a --filter name=htm-release-test --format '{{.Names}}'
   ```
   - 既存のコンテナがあれば先に削除:
     ```bash
     docker stop htm-release-test 2>/dev/null; docker rm htm-release-test 2>/dev/null
     ```

2. **ポート使用状況の確認**
   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/ 2>/dev/null || echo "port_free"
   ```
   - ポート8888が使用中の場合: 使用中のサービスを報告し、停止を促して中断

3. **ビルド**
   ```bash
   docker build -t html-tool-manager:release-test .
   ```

4. **起動**
   ```bash
   docker run -d -p 8888:80 --name htm-release-test html-tool-manager:release-test
   ```

5. **ヘルスチェック**（リトライ付き）
   - 最大30秒間、5秒間隔でヘルスチェックを実行（以下を単一スクリプトとして実行）:
     ```bash
     HEALTH_STATUS="unhealthy"
     for i in 1 2 3 4 5 6; do
       if curl -s -f http://localhost:8888/ > /dev/null 2>&1; then
         HEALTH_STATUS="healthy"
         break
       fi
       sleep 5
     done
     echo "$HEALTH_STATUS"
     ```
   - `healthy` が返れば成功
   - `unhealthy` の場合: `docker logs htm-release-test` でログを確認して報告

6. **クリーンアップ**（成功・失敗に関わらず必ず実行）
   ```bash
   docker stop htm-release-test || true
   docker rm htm-release-test || true
   docker rmi html-tool-manager:release-test || true
   ```

## Phase 4: バージョン決定

1. **最新タグと変更履歴を取得**
   ```bash
   git describe --tags --abbrev=0 2>/dev/null || echo "NO_TAGS"
   ```
   - タグが存在する場合:
     ```bash
     git log $(git describe --tags --abbrev=0)..HEAD --oneline
     ```
   - **タグが存在しない場合（初回リリース）**:
     - `NO_TAGS` が返る
     - 全コミット履歴を取得:
       ```bash
       git log --oneline
       ```
     - 初回リリースとして `0.1.0` を基準に提案

2. **バージョンを決定**
   - **初回リリースの場合**: 引数がなければ `0.1.0` を提案
   - 引数がある場合: 引数に従ってバージョンを計算
   - 引数がない場合: 変更内容を分析して提案
     - `feat:` があれば minor を提案
     - `fix:` のみなら patch を提案
     - `BREAKING CHANGE:` や `!:` があれば major を提案

3. **ユーザーに確認**
   - 変更履歴のサマリーを表示
   - 提案するバージョンを表示
   - 続行するか確認を取る

## Phase 5: リリース実行

1. **pyproject.toml のバージョンを更新**
   - Editツールで `version = "x.y.z"` の行を新しいバージョンに書き換える

2. **変更をコミット**
   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to <version>"
   ```

3. **タグメッセージを作成**
   - 変更履歴を整形してタグメッセージにする

4. **タグを作成**
   ```bash
   git tag -a v<version> -m "<message>"
   ```

5. **プッシュの確認**
   - 作成されたタグを表示
   - **重要**: `git push origin main v<version>` を実行するか明示的に確認を取る
   - ユーザーの承認なしにプッシュしない

6. **プッシュ実行**（承認後のみ）
   ```bash
   git push origin main v<version>
   ```

7. **完了報告**
   - 作成されたタグ名
   - 次のアクション（GitHub Releasesでのリリースノート作成など）

## 注意事項

- **破壊的操作**: タグのプッシュは取り消しが難しいため、必ずユーザー確認を取る
- **Dockerクリーンアップ**: テスト用コンテナ・イメージは必ず削除する
- **エラー時の中断**: 各フェーズで問題が発生したら、その時点で中断して報告する
- **セキュリティ警告**: LOWレベルは許容可能、HIGH/MEDIUMは対応が必要
