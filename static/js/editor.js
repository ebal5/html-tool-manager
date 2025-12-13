/**
 * Ace Editor 統合モジュール
 * HTML/CSS/JavaScriptのシンタックスハイライト機能を提供
 */

/**
 * ツールタイプからAceモードを取得
 * @param {string} toolType - ツールタイプ ('html' | 'react' | '')
 * @returns {string} - Aceモード名
 */
function getAceModeForToolType(toolType) {
  return toolType === 'react' ? 'ace/mode/jsx' : 'ace/mode/html';
}

/**
 * エディタのモードを切り替え
 * @param {object} editor - Ace Editorインスタンス
 * @param {string} toolType - ツールタイプ ('html' | 'react' | '')
 */
// biome-ignore lint/correctness/noUnusedVariables: HTMLテンプレートから呼び出される
function setEditorMode(editor, toolType) {
  if (editor) {
    editor.session.setMode(getAceModeForToolType(toolType));
  }
}

/**
 * Ace Editorを初期化
 * @param {string} textareaId - 置き換え対象のtextareaのID
 * @param {string} editorId - 作成するエディタコンテナのID
 * @param {string} [toolType='html'] - ツールタイプ ('html' | 'react')
 * @returns {object|null} - Ace Editorインスタンスまたはnull
 */
// biome-ignore lint/correctness/noUnusedVariables: HTMLテンプレートから呼び出される
function initializeAceEditor(textareaId, editorId, toolType = 'html') {
  const textarea = document.getElementById(textareaId);
  if (!textarea) {
    console.error('Textarea not found:', textareaId);
    return null;
  }

  // Aceが読み込まれているか確認
  if (typeof ace === 'undefined') {
    console.error('Ace Editor is not loaded');
    return null;
  }

  // 親要素の存在確認
  if (!textarea.parentNode) {
    console.error('Textarea has no parent element');
    return null;
  }

  // エディタコンテナを作成
  const editorContainer = document.createElement('div');
  editorContainer.id = editorId;
  editorContainer.style.width = '100%';
  editorContainer.style.height = '400px';
  editorContainer.style.border = '1px solid var(--pico-muted-border-color)';
  editorContainer.style.borderRadius = 'var(--pico-border-radius)';

  // textareaの後にエディタを挿入
  textarea.style.display = 'none';
  textarea.parentNode.insertBefore(editorContainer, textarea.nextSibling);

  // Ace Editorを初期化
  const editor = ace.edit(editorId);

  // エディタ設定
  editor.setTheme('ace/theme/monokai');
  editor.session.setMode(getAceModeForToolType(toolType));
  editor.setOptions({
    fontSize: '14px',
    showLineNumbers: true,
    showGutter: true,
    highlightActiveLine: true,
    showPrintMargin: false,
    tabSize: 2,
    useSoftTabs: true,
    wrap: true,
  });

  // 初期値をセット
  editor.setValue(textarea.value, -1);

  // エディタの変更をtextareaに同期
  editor.session.on('change', () => {
    textarea.value = editor.getValue();
  });

  return editor;
}
