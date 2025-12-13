/**
 * テーマ管理モジュール
 * Pico.cssのdata-theme属性を使用してダークモード切り替えを実装
 */

/**
 * @typedef {'light' | 'dark' | 'auto'} ThemePreference
 */

/**
 * 利用可能なテーマ設定
 * @type {Readonly<{LIGHT: 'light', DARK: 'dark', AUTO: 'auto'}>}
 */
const THEMES = Object.freeze({
  LIGHT: 'light',
  DARK: 'dark',
  AUTO: 'auto',
});

/** @type {ReadonlySet<string>} 有効なテーマ値のセット */
const VALID_THEMES = new Set([THEMES.LIGHT, THEMES.DARK, THEMES.AUTO]);

const STORAGE_KEY = 'theme-preference';

/**
 * テーマ切り替えボタンに表示するアイコン
 * @type {Readonly<Record<ThemePreference, string>>}
 */
const THEME_ICONS = Object.freeze({
  [THEMES.LIGHT]: '\u2600\uFE0F',
  [THEMES.DARK]: '\uD83C\uDF19',
  [THEMES.AUTO]: '\uD83D\uDDA5\uFE0F',
});

/**
 * テーマ切り替えボタンのラベル
 * @type {Readonly<Record<ThemePreference, string>>}
 */
const THEME_LABELS = Object.freeze({
  [THEMES.LIGHT]: 'ライトモード',
  [THEMES.DARK]: 'ダークモード',
  [THEMES.AUTO]: 'システム設定',
});

/**
 * テーマサイクル順序: light → dark → auto → light
 * @type {Readonly<Record<ThemePreference, ThemePreference>>}
 */
const THEME_CYCLE = Object.freeze({
  [THEMES.LIGHT]: THEMES.DARK,
  [THEMES.DARK]: THEMES.AUTO,
  [THEMES.AUTO]: THEMES.LIGHT,
});

/**
 * システムのカラースキーム設定を取得
 * @returns {'light' | 'dark'} システムのテーマ
 */
function getSystemTheme() {
  if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return THEMES.DARK;
  }
  return THEMES.LIGHT;
}

/**
 * 保存されたテーマ設定を取得
 * @returns {ThemePreference} 保存されたテーマ、なければ "auto"
 */
function getSavedTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    // 不正な値が保存されている場合はデフォルトに戻す
    if (saved && VALID_THEMES.has(saved)) {
      return saved;
    }
    return THEMES.AUTO;
  } catch {
    return THEMES.AUTO;
  }
}

/**
 * テーマ設定を保存
 * @param {ThemePreference} theme - 保存するテーマ
 */
function saveTheme(theme) {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch (error) {
    console.warn('Failed to save theme preference:', error);
  }
}

/**
 * 実際に適用するテーマを決定
 * @param {ThemePreference} preference - ユーザーのテーマ設定
 * @returns {'light' | 'dark'} 適用するテーマ
 */
function resolveTheme(preference) {
  if (preference === THEMES.AUTO) {
    return getSystemTheme();
  }
  return preference;
}

/**
 * テーマをDOMに適用
 * @param {'light' | 'dark'} theme - 適用するテーマ
 */
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

/**
 * テーマを初期化（FLASH防止のため、できるだけ早く実行）
 */
function initTheme() {
  const savedPreference = getSavedTheme();
  const actualTheme = resolveTheme(savedPreference);
  applyTheme(actualTheme);
}

/**
 * テーマ切り替えボタンの状態を更新
 * @param {ThemePreference} preference - 現在のテーマ設定
 */
function updateThemeButton(preference) {
  const button = document.getElementById('theme-toggle');
  if (!button) return;

  button.textContent = THEME_ICONS[preference] || THEME_ICONS[THEMES.AUTO];
  button.setAttribute(
    'aria-label',
    THEME_LABELS[preference] || THEME_LABELS[THEMES.AUTO],
  );
  button.setAttribute(
    'title',
    THEME_LABELS[preference] || THEME_LABELS[THEMES.AUTO],
  );
}

/**
 * テーマを切り替える
 */
function cycleTheme() {
  const currentPreference = getSavedTheme();
  const newPreference = THEME_CYCLE[currentPreference] || THEMES.AUTO;
  const actualTheme = resolveTheme(newPreference);

  saveTheme(newPreference);
  applyTheme(actualTheme);
  updateThemeButton(newPreference);
}

/**
 * システムのカラースキーム変更を監視
 */
function watchSystemTheme() {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

  // システム設定が変更された時、autoモードの場合のみ更新
  mediaQuery.addEventListener('change', () => {
    const currentPreference = getSavedTheme();
    if (currentPreference === THEMES.AUTO) {
      applyTheme(getSystemTheme());
    }
  });
}

/**
 * DOMContentLoaded時の初期化
 */
function setupThemeToggle() {
  const button = document.getElementById('theme-toggle');
  if (button) {
    button.addEventListener('click', cycleTheme);
    updateThemeButton(getSavedTheme());
  }

  watchSystemTheme();
}

// FLASH防止: スクリプト読み込み時に即座にテーマを適用
initTheme();

// DOMContentLoaded時にボタンのイベントリスナーを設定
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupThemeToggle);
} else {
  // すでにDOMが読み込まれている場合
  setupThemeToggle();
}
