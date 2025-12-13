/**
 * キーボードショートカット管理モジュール
 *
 * 機能:
 * - ショートカットの登録
 * - ページコンテキスト検出
 * - フォーム入力中の競合回避
 */

// biome-ignore lint/correctness/noUnusedVariables: グローバルに公開するモジュール
const KeyboardShortcuts = (() => {
  /**
   * アクティブ要素がテキスト入力中かどうかを判定
   * @returns {boolean}
   */
  function isInputActive() {
    const el = document.activeElement;
    if (!el) return false;

    const tag = el.tagName.toLowerCase();

    // textarea
    if (tag === 'textarea') return true;

    // contenteditable
    if (el.isContentEditable) return true;

    // input (text系)
    if (tag === 'input') {
      const type = (el.type || 'text').toLowerCase();
      const textTypes = ['text', 'search', 'email', 'password', 'tel', 'url'];
      return textTypes.includes(type);
    }

    // Ace Editor内
    if (el.classList.contains('ace_text-input')) return true;

    return false;
  }

  /**
   * 現在のページコンテキストを取得
   * @returns {'index'|'create'|'edit'|'view'|'unknown'}
   */
  function getCurrentPageContext() {
    const path = window.location.pathname;

    if (path === '/') return 'index';
    if (path === '/tools/create') return 'create';
    if (path.startsWith('/tools/edit/')) return 'edit';
    if (path.startsWith('/tools/view/')) return 'view';

    return 'unknown';
  }

  /**
   * ヘルプモーダルを開く
   */
  function openHelpModal() {
    const dialog = document.getElementById('help-modal');
    if (dialog) {
      dialog.showModal();
    }
  }

  /**
   * ヘルプモーダルを閉じる
   */
  function closeHelpModal() {
    const dialog = document.getElementById('help-modal');
    if (dialog?.open) {
      dialog.close();
    }
  }

  /**
   * 開いているモーダルを閉じる
   */
  function closeAnyModal() {
    // コマンドパレット
    if (typeof CommandPalette !== 'undefined' && CommandPalette.isOpen()) {
      CommandPalette.close();
      return true;
    }

    // ヘルプモーダル
    const helpModal = document.getElementById('help-modal');
    if (helpModal?.open) {
      helpModal.close();
      return true;
    }

    return false;
  }

  /**
   * 編集ページのIDを取得（index.htmlで使用）
   * @returns {string|null}
   */
  function getSelectedToolId() {
    // チェックボックスで選択されたツールを取得
    const checkbox = document.querySelector('.tool-checkbox:checked');
    if (checkbox) {
      const row = checkbox.closest('tr');
      return row ? row.dataset.toolId : null;
    }
    return null;
  }

  /**
   * 現在のページのツールIDを取得（view/editページ用）
   * @returns {string|null}
   */
  function getCurrentToolId() {
    const path = window.location.pathname;
    const match = path.match(/\/tools\/(?:view|edit)\/(\d+)/);
    return match ? match[1] : null;
  }

  /**
   * フォームを送信する
   */
  function submitForm() {
    const form = document.querySelector('form');
    if (form) {
      // requestSubmitを使用してvalidationを実行
      form.requestSubmit();
    }
  }

  /**
   * ショートカットを初期化
   */
  function init() {
    // hotkeysが利用可能か確認
    if (typeof hotkeys === 'undefined') {
      console.warn('hotkeys-js is not loaded');
      return;
    }

    const context = getCurrentPageContext();

    // フォーム内でもCtrl+Sを有効にする設定
    hotkeys.filter = (event) => {
      const target = event.target || event.srcElement;
      const tag = target.tagName;

      // Ctrl+SとEscapeは常に有効
      if (event.key === 's' && (event.ctrlKey || event.metaKey)) {
        return true;
      }
      if (event.key === 'Escape') {
        return true;
      }

      // それ以外は通常の入力要素では無効
      return !(
        target.isContentEditable ||
        tag === 'INPUT' ||
        tag === 'SELECT' ||
        tag === 'TEXTAREA'
      );
    };

    // Ctrl+K: コマンドパレット
    hotkeys('ctrl+k,command+k', (event) => {
      event.preventDefault();
      if (typeof CommandPalette !== 'undefined') {
        CommandPalette.open();
      }
    });

    // Ctrl+N: 新規作成（create, editページ以外）
    if (context !== 'create' && context !== 'edit') {
      hotkeys('ctrl+n,command+n', (event) => {
        event.preventDefault();
        window.location.href = '/tools/create';
      });
    }

    // Ctrl+E: 編集（createページ以外）
    if (context !== 'create' && context !== 'edit') {
      hotkeys('ctrl+e,command+e', (event) => {
        event.preventDefault();

        let toolId = null;

        if (context === 'view') {
          toolId = getCurrentToolId();
        } else if (context === 'index') {
          toolId = getSelectedToolId();
        }

        if (toolId) {
          window.location.href = `/tools/edit/${toolId}`;
        }
      });
    }

    // Ctrl+S: 保存（create, editページのみ）
    if (context === 'create' || context === 'edit') {
      hotkeys('ctrl+s,command+s', (event) => {
        event.preventDefault();
        submitForm();
      });
    }

    // Ctrl+/: ヘルプ表示
    hotkeys('ctrl+/,command+/', (event) => {
      event.preventDefault();
      const helpModal = document.getElementById('help-modal');
      if (helpModal) {
        if (helpModal.open) {
          helpModal.close();
        } else {
          helpModal.showModal();
        }
      }
    });

    // Escape: モーダルを閉じる
    hotkeys('escape', (event) => {
      if (closeAnyModal()) {
        event.preventDefault();
      }
    });

    // ヘルプモーダルの閉じるボタン
    const helpCloseBtn = document.querySelector(
      '#help-modal [data-close-modal]',
    );
    if (helpCloseBtn) {
      helpCloseBtn.addEventListener('click', closeHelpModal);
    }

    // ヘルプモーダルの背景クリックで閉じる
    const helpModal = document.getElementById('help-modal');
    if (helpModal) {
      helpModal.addEventListener('click', (e) => {
        if (e.target === helpModal) {
          helpModal.close();
        }
      });
    }
  }

  // DOMContentLoadedで初期化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return {
    isInputActive,
    getCurrentPageContext,
    openHelpModal,
    closeHelpModal,
  };
})();
