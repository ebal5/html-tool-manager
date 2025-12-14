/**
 * コマンドパレットUIモジュール
 *
 * 機能:
 * - モーダルの表示/非表示
 * - ツール検索（既存APIを利用）
 * - キーボードナビゲーション（矢印キー、Enter）
 */

// biome-ignore lint/correctness/noUnusedVariables: keyboard-shortcuts.jsから参照
const CommandPalette = (() => {
  /** 検索デバウンス遅延（ミリ秒） */
  const SEARCH_DEBOUNCE_MS = 300;

  let dialog = null;
  let searchInput = null;
  let resultsList = null;
  let selectedIndex = -1;
  let debounceTimer = null;
  let tools = [];

  /**
   * コマンドパレットを初期化
   */
  function init() {
    dialog = document.getElementById('command-palette');
    searchInput = document.getElementById('command-palette-search');
    resultsList = document.getElementById('command-palette-results');

    if (!dialog || !searchInput || !resultsList) {
      return;
    }

    // 閉じるボタンのイベント
    const closeBtn = dialog.querySelector('[data-close-modal]');
    if (closeBtn) {
      closeBtn.addEventListener('click', close);
    }

    // 検索入力のイベント
    searchInput.addEventListener('input', handleSearchInput);
    searchInput.addEventListener('keydown', handleSearchKeydown);

    // ダイアログの背景クリックで閉じる
    dialog.addEventListener('click', (e) => {
      if (e.target === dialog) {
        close();
      }
    });

    // ダイアログのcancel（Escキー）イベント
    dialog.addEventListener('cancel', (e) => {
      e.preventDefault();
      close();
    });
  }

  /**
   * コマンドパレットを開く
   */
  function open() {
    if (!dialog) return;
    dialog.showModal();
    searchInput.value = '';
    selectedIndex = -1;
    tools = [];
    showHint();
    searchInput.focus();
  }

  /**
   * コマンドパレットを閉じる
   */
  function close() {
    if (!dialog) return;
    clearTimeout(debounceTimer);
    dialog.close();
  }

  /**
   * パレットが開いているか確認
   * @returns {boolean}
   */
  function isOpen() {
    return dialog?.open;
  }

  /**
   * 検索入力のハンドラ
   */
  function handleSearchInput() {
    clearTimeout(debounceTimer);
    const query = searchInput.value.trim();

    // コロンで終わる場合は検索しない（クエリ構文対応）
    if (query.endsWith(':')) {
      return;
    }

    // 空クエリの場合はヒントを表示
    if (query.length === 0) {
      showHint();
      return;
    }

    debounceTimer = setTimeout(() => searchTools(query), SEARCH_DEBOUNCE_MS);
  }

  /**
   * 検索ヒントを表示
   */
  function showHint() {
    tools = [];
    selectedIndex = -1;
    resultsList.innerHTML = '';
    const li = document.createElement('li');
    li.className = 'hint';
    li.textContent = 'キーワードを入力して検索';
    resultsList.appendChild(li);
  }

  /**
   * 検索入力でのキーボードイベント
   * @param {KeyboardEvent} e
   */
  function handleSearchKeydown(e) {
    const items = resultsList.querySelectorAll('li');

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
        updateSelection(items);
        break;
      case 'ArrowUp':
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, -1);
        updateSelection(items);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < tools.length) {
          navigateToTool(tools[selectedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        close();
        break;
    }
  }

  /**
   * 選択状態を更新
   * @param {NodeListOf<HTMLLIElement>} items
   */
  function updateSelection(items) {
    items.forEach((item, index) => {
      item.setAttribute(
        'aria-selected',
        index === selectedIndex ? 'true' : 'false',
      );
    });

    // 選択項目をスクロールして表示
    if (selectedIndex >= 0 && items[selectedIndex]) {
      items[selectedIndex].scrollIntoView({ block: 'nearest' });
    }
  }

  /**
   * ツールを検索
   * @param {string} query
   */
  async function searchTools(query) {
    try {
      const params = new URLSearchParams();
      if (query) params.append('q', query);

      const response = await fetch(`/api/tools/?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      tools = await response.json();
      renderResults();
    } catch (error) {
      console.error('Error searching tools:', error);
      resultsList.innerHTML = '';
      const li = document.createElement('li');
      li.className = 'error';
      li.textContent = '検索中にエラーが発生しました';
      resultsList.appendChild(li);
    }
  }

  /**
   * 検索結果を描画
   */
  function renderResults() {
    resultsList.innerHTML = '';
    selectedIndex = -1;

    if (tools.length === 0) {
      const li = document.createElement('li');
      li.className = 'no-results';
      li.textContent = 'ツールが見つかりませんでした';
      resultsList.appendChild(li);
      return;
    }

    tools.forEach((tool, index) => {
      const li = document.createElement('li');
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', 'false');
      li.dataset.toolId = tool.id;

      const nameSpan = document.createElement('span');
      nameSpan.className = 'tool-name';
      nameSpan.textContent = tool.name;

      const descSpan = document.createElement('span');
      descSpan.className = 'tool-description';
      descSpan.textContent = tool.description || '';

      li.appendChild(nameSpan);
      if (tool.description) {
        li.appendChild(descSpan);
      }

      li.addEventListener('click', () => navigateToTool(tool));
      li.addEventListener('mouseenter', () => {
        selectedIndex = index;
        updateSelection(resultsList.querySelectorAll('li'));
      });

      resultsList.appendChild(li);
    });
  }

  /**
   * ツールページに移動
   * @param {Object} tool
   */
  function navigateToTool(tool) {
    close();
    window.location.href = `/tools/view/${tool.id}`;
  }

  // DOMContentLoadedで初期化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return {
    open,
    close,
    isOpen,
  };
})();
