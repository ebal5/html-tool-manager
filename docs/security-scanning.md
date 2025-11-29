# Dockerイメージセキュリティスキャン

## 概要

このプロジェクトでは、複数レイヤーのセキュリティスキャンを実施しています：

1. **Pythonコード**: bandit によるコード脆弱性スキャン
2. **Python依存関係**: pip-audit による既知の脆弱性チェック
3. **Dockerイメージ**: Trivy によるOSパッケージとアプリケーション依存関係のスキャン

## Dockerイメージスキャンの実装

### 目的

- リリース前にDockerイメージ内の脆弱性を検出
- CRITICAL/HIGH の脆弱性が見つかった場合、自動的にリリースを中止
- GitHub Security タブで脆弱性を一元管理

### 実装方法

`.github/workflows/docker-publish.yml` に以下の変更を加えます。

### 1. パーミッションの追加

SARIF形式の結果をGitHub Securityにアップロードするため、`security-events: write` 権限が必要です：

```yaml
permissions:
  contents: write
  packages: write
  security-events: write  # Trivy結果のアップロードに必要
```

### 2. スキャンステップの追加

既存の「Build and push Docker image」ステップの**前**に、以下のステップを追加します：

```yaml
      - name: Build Docker image for scanning
        uses: docker/build-push-action@v6
        with:
          context: .
          push: false
          load: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:scan
          cache-from: type=gha

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:scan'
          format: 'sarif'
          output: 'trivy-results.sarif'
          exit-code: '1'
          ignore-unfixed: true
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
```

### 設定パラメータの説明

| パラメータ | 値 | 説明 |
|----------|-----|------|
| `format` | `sarif` | GitHub Security タブと互換性のある形式 |
| `exit-code` | `1` | 脆弱性が見つかった場合、ワークフローを失敗させる |
| `ignore-unfixed` | `true` | まだ修正版がリリースされていない脆弱性は無視 |
| `severity` | `CRITICAL,HIGH` | 重大度が高い脆弱性のみ検出 |

### 2段階ビルドのトレードオフ

このワークフローではスキャン用のイメージと本番用のイメージを2回ビルドします：

**理由**:
- スキャン用ビルド（`load: true`, `push: false`）でローカルにイメージを作成
- Trivyでスキャン実行後、脆弱性がなければ本番用ビルドを実行

**メリット**:
- CRITICAL/HIGH脆弱性検出時に**リリースを自動中止**できる
- 脆弱なイメージがレジストリにプッシュされることを防止

**デメリット**:
- CI時間が増加する可能性（特にマルチプラットフォームビルド時）
- キャッシュを活用しているため、実際の増加は最小限に抑えられる

**注意**: スキャン用ビルドはマルチプラットフォーム（linux/amd64, linux/arm64）ではなく、単一プラットフォームでビルドされます。これはスキャン速度を優先した設計です。

### ワークフローの動作

1. **スキャン用イメージビルド**: ローカルにイメージをビルド（プッシュなし）
2. **Trivyスキャン実行**: CRITICAL/HIGH の脆弱性を検出
3. **結果アップロード**: SARIF形式でGitHub Securityにアップロード
4. **判定**:
   - ✅ 脆弱性なし → 次のステップ（本番ビルド＆プッシュ）へ進む
   - ❌ 脆弱性あり → ワークフロー失敗、リリース中止

### 脆弱性が見つかった場合の対応フロー

1. **GitHub Security タブで詳細確認**
   - 脆弱性の内容、影響範囲、CVE番号を確認

2. **修正方法の検討**
   - ベースイメージの更新（`Dockerfile` の `FROM` 行）
   - 依存パッケージのバージョン更新（`pyproject.toml`）
   - 代替パッケージへの移行

3. **修正後の再スキャン**
   - 修正をコミット＆プッシュ
   - ワークフローが自動的に再実行される

4. **リリース継続**
   - スキャンがパスすれば、自動的にイメージがプッシュされる

### ローカルでのスキャン実行

リリース前にローカルでスキャンを実行することも可能です：

```bash
# イメージをビルド
docker build -t html-tool-manager:local .

# Trivyスキャン実行
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity CRITICAL,HIGH html-tool-manager:local
```

### 定期スキャンの設定（オプション）

新しい脆弱性は日々発見されるため、既存イメージの定期スキャンも推奨されます：

```yaml
# .github/workflows/scheduled-scan.yml（新規作成）
name: Scheduled Security Scan

on:
  schedule:
    - cron: '0 0 * * 0'  # 毎週日曜日 0:00 UTC
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      packages: read
      security-events: write
    steps:
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Run Trivy scanner on latest image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

## 参考リンク

- [Trivy 公式ドキュメント](https://aquasecurity.github.io/trivy/)
- [Trivy GitHub Action](https://github.com/aquasecurity/trivy-action)
- [Docker セキュリティベストプラクティス](https://docs.docker.com/develop/security-best-practices/)
- [GitHub Security Overview](https://docs.github.com/en/code-security/security-overview/about-security-overview)
