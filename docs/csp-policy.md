# Content Security Policy (CSP) 対応方針

## 概要

このプロジェクトでは、XSS（クロスサイトスクリプティング）攻撃を防ぐため、Content Security Policyを実装しています。

## CSP設定の実装

### 設定場所

`src/html_tool_manager/main.py` のセキュリティミドルウェア内で設定しています。

### 現在のCSPポリシー

```
default-src 'self';
script-src 'self' https://unpkg.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com 'unsafe-inline' 'unsafe-eval';
style-src 'self' https://cdn.jsdelivr.net https://cdn.tailwindcss.com 'unsafe-inline';
img-src 'self' data:;
connect-src 'self' https://cdn.jsdelivr.net;
worker-src 'self' blob:;
frame-ancestors 'none';
base-uri 'self';
```

### ディレクティブの説明

| ディレクティブ | 設定値 | 理由 |
|---------------|--------|------|
| `default-src` | `'self'` | デフォルトは同一オリジンのみ許可 |
| `script-src` | `'self'` + CDN + `'unsafe-inline'` + `'unsafe-eval'` | Ace Editor、Pico.css等のCDN利用のため |
| `style-src` | `'self'` + CDN + `'unsafe-inline'` | Pico.css、Tailwind等のCDN利用と動的スタイルのため |
| `img-src` | `'self' data:` | インライン画像（data URI）の許可 |
| `connect-src` | `'self'` + CDN | JSライブラリのES Module読み込みのため |
| `worker-src` | `'self' blob:` | Ace EditorのWeb Worker対応 |
| `frame-ancestors` | `'none'` | クリックジャッキング対策 |
| `base-uri` | `'self'` | base要素のURL制限 |

## 2つのセキュリティモード

### 1. アプリケーション本体

- **パス**: `/tool-files/` 以外のすべて
- **CSP**: 完全なCSPポリシーを適用
- **保護レベル**: 高

### 2. ツール用HTML（ユーザーアップロードコンテンツ）

- **パス**: `/tool-files/*`
- **CSP**: 設定しない
- **代替保護**: iframe sandbox属性で隔離

**理由**: ツールごとに使用するCDN（Chart.js、D3.js、Three.js等）が異なり、すべてのCDNを許可リストに追加することは現実的ではないため、sandbox属性による隔離を採用しています。

## コーディングガイドライン

### ✅ 推奨されるパターン

#### JavaScript

```javascript
// DOM APIを使用して要素を作成（XSS対策）
const div = document.createElement('div');
div.textContent = userInput;  // textContentは自動エスケープ
div.className = 'my-class';

// イベントハンドラはaddEventListenerで追加
button.addEventListener('click', handleClick);
```

#### CSS

```css
/* スタイルはCSSファイルで定義 */
.error-message {
  color: var(--pico-color-red-500);
}
```

### ❌ 避けるべきパターン

```javascript
// インラインHTML（XSSリスク）
element.innerHTML = userInput;

// インラインスタイル属性（将来的にCSP厳格化の障害）
element.style.color = 'red';

// インラインイベントハンドラ（CSP違反の可能性）
element.onclick = handleClick;
```

## 将来の改善計画

### Phase 1: 現状（実施済み）

- `'unsafe-inline'` を許可してCDNライブラリとの互換性を確保
- XSS対策はDOM API使用を徹底

### Phase 2: インラインスタイルの排除（検討中）

- すべてのインラインスタイルをCSSクラスに移行
- `style-src` から `'unsafe-inline'` を削除可能に

### Phase 3: nonce/hashベースのCSP（将来）

- `'unsafe-inline'` の代わりにnonce属性またはhashを使用
- より厳格なCSPポリシーの実現

## 他のセキュリティヘッダー

CSP以外にも以下のセキュリティヘッダーを設定しています：

| ヘッダー | 値 | 目的 |
|---------|-----|------|
| `X-Content-Type-Options` | `nosniff` | MIMEスニッフィング防止 |
| `X-Frame-Options` | `SAMEORIGIN` | クリックジャッキング対策 |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | リファラー情報の制御 |

## 参考リンク

- [MDN: Content Security Policy](https://developer.mozilla.org/ja/docs/Web/HTTP/CSP)
- [OWASP: Content Security Policy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- [CSP Evaluator (Google)](https://csp-evaluator.withgoogle.com/)
