/**
 * テーマ管理モジュール
 * Pico.cssのdata-theme属性を使用してダークモード切り替えを実装
 */

const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
  AUTO: 'auto',
};

const STORAGE_KEY = 'theme-preference';

/**
 * システムのカラースキーム設定を取得
 * @returns {string} "light" または "dark"
 */
function getSystemTheme() {
  if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return THEMES.DARK;
  }
  return THEMES.LIGHT;
}

/**
 * 保存されたテーマ設定を取得
 * @returns {string} 保存されたテーマ、なければ "auto"
 */
function getSavedTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY) || THEMES.AUTO;
  } catch {
    return THEMES.AUTO;
  }
}

/**
 * テーマ設定を保存
 * @param {string} theme - 保存するテーマ
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
 * @param {string} preference - ユーザーのテーマ設定（"light"/"dark"/"auto"）
 * @returns {string} 適用するテーマ（"light" または "dark"）
 */
function resolveTheme(preference) {
  if (preference === THEMES.AUTO) {
    return getSystemTheme();
  }
  return preference;
}

/**
 * テーマをDOMに適用
 * @param {string} theme - 適用するテーマ（"light" または "dark"）
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
 * @param {string} preference - 現在のテーマ設定
 */
function updateThemeButton(preference) {
  const button = document.getElementById('theme-toggle');
  if (!button) return;

  const icons = {
    [THEMES.LIGHT]: '\u2600\uFE0F',
    [THEMES.DARK]: '\uD83C\uDF19',
    [THEMES.AUTO]: '\uD83D\uDDA5\uFE0F',
  };

  const labels = {
    [THEMES.LIGHT]: 'ライトモード',
    [THEMES.DARK]: 'ダークモード',
    [THEMES.AUTO]: 'システム設定',
  };

  button.textContent = icons[preference] || icons[THEMES.AUTO];
  button.setAttribute('aria-label', labels[preference] || labels[THEMES.AUTO]);
  button.setAttribute('title', labels[preference] || labels[THEMES.AUTO]);
}

/**
 * テーマを切り替える
 */
function cycleTheme() {
  const currentPreference = getSavedTheme();

  // light → dark → auto → light のサイクル
  const cycle = {
    [THEMES.LIGHT]: THEMES.DARK,
    [THEMES.DARK]: THEMES.AUTO,
    [THEMES.AUTO]: THEMES.LIGHT,
  };

  const newPreference = cycle[currentPreference] || THEMES.AUTO;
  const actualTheme = resolveTheme(newPreference);

  saveTheme(newPreference);
  applyTheme(actualTheme);
  updateThemeButton(newPreference);
}

/**
 * システムのカラースキーム変更を監視
 */
function watchSystemTheme() {
  if (!window.matchMedia) return;

  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

  // システム設定が変更された時、autoモードの場合のみ更新
  const handleChange = () => {
    const currentPreference = getSavedTheme();
    if (currentPreference === THEMES.AUTO) {
      const actualTheme = getSystemTheme();
      applyTheme(actualTheme);
    }
  };

  // Modern browsers
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', handleChange);
  } else {
    // Legacy browsers
    mediaQuery.addListener(handleChange);
  }
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
