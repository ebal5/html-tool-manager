/**
 * スナップショット（履歴）管理モジュール
 */

// diff2html CDN URLs
const DIFF2HTML_CSS =
  'https://cdn.jsdelivr.net/npm/diff2html/bundles/css/diff2html.min.css';
const DIFF2HTML_JS =
  'https://cdn.jsdelivr.net/npm/diff2html/bundles/js/diff2html-ui.min.js';
const DIFF_JS = 'https://cdn.jsdelivr.net/npm/diff/dist/diff.min.js';

let diff2htmlLoaded = false;

/**
 * スクリプトを動的に読み込む
 * @param {string} src - スクリプトのURL
 * @returns {Promise<void>}
 */
function loadScript(src) {
  return new Promise((resolve, reject) => {
    // 既に読み込まれているか確認
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

/**
 * CSSを動的に読み込む
 * @param {string} href - CSSのURL
 */
function loadCSS(href) {
  if (document.querySelector(`link[href="${href}"]`)) {
    return;
  }
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = href;
  document.head.appendChild(link);
}

/**
 * diff2html ライブラリを動的に読み込む
 * @returns {Promise<void>}
 */
async function loadDiff2Html() {
  if (diff2htmlLoaded) return;

  // CSS読み込み
  loadCSS(DIFF2HTML_CSS);

  // diff.js読み込み
  await loadScript(DIFF_JS);

  // diff2html-ui.js読み込み
  await loadScript(DIFF2HTML_JS);

  diff2htmlLoaded = true;
}

/**
 * スナップショット一覧を取得して表示
 * @param {number} toolId - ツールID
 * @param {HTMLElement} container - 表示先コンテナ
 */
async function fetchSnapshots(toolId, container) {
  container.innerHTML = '<p aria-busy="true">履歴を読み込み中...</p>';

  try {
    const response = await fetch(`/api/tools/${toolId}/snapshots`);
    if (!response.ok) throw new Error('Failed to fetch snapshots');

    const snapshots = await response.json();
    renderSnapshotList(snapshots, container, toolId);
  } catch (error) {
    container.innerHTML =
      '<p style="color: var(--pico-color-red-500);">履歴の読み込みに失敗しました。</p>';
    console.error('Error fetching snapshots:', error);
  }
}

/**
 * スナップショット一覧をレンダリング
 * @param {Array} snapshots - スナップショット配列
 * @param {HTMLElement} container - 表示先コンテナ
 * @param {number} toolId - ツールID
 */
function renderSnapshotList(snapshots, container, toolId) {
  if (snapshots.length === 0) {
    container.innerHTML =
      '<p>履歴がありません。ツールを更新すると自動的に履歴が作成されます。</p>';
    return;
  }

  const header = document.createElement('div');
  header.className = 'snapshot-header';

  const createBtn = document.createElement('button');
  createBtn.id = 'create-snapshot-btn';
  createBtn.className = 'secondary outline';
  createBtn.textContent = '手動スナップショット作成';
  header.appendChild(createBtn);

  const table = document.createElement('table');
  table.className = 'snapshot-table';

  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th>日時</th>
      <th>名前</th>
      <th>種類</th>
      <th>操作</th>
    </tr>
  `;
  table.appendChild(thead);

  const tbody = document.createElement('tbody');

  for (const snapshot of snapshots) {
    const tr = document.createElement('tr');
    tr.dataset.snapshotId = snapshot.id;

    const dateCell = document.createElement('td');
    dateCell.textContent = formatDate(snapshot.created_at);

    const nameCell = document.createElement('td');
    nameCell.textContent = snapshot.name || '-';

    const typeCell = document.createElement('td');
    const typeBadge = document.createElement('code');
    typeBadge.textContent = snapshot.snapshot_type === 'auto' ? '自動' : '手動';
    typeBadge.className =
      snapshot.snapshot_type === 'auto'
        ? 'snapshot-type-auto'
        : 'snapshot-type-manual';
    typeCell.appendChild(typeBadge);

    const actionsCell = document.createElement('td');
    actionsCell.className = 'snapshot-actions';

    const diffBtn = document.createElement('button');
    diffBtn.className = 'diff-btn secondary outline';
    diffBtn.dataset.snapshotId = snapshot.id;
    diffBtn.textContent = '差分';

    const restoreBtn = document.createElement('button');
    restoreBtn.className = 'restore-btn primary outline';
    restoreBtn.dataset.snapshotId = snapshot.id;
    restoreBtn.textContent = '復元';

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'delete-snapshot-btn contrast outline';
    deleteBtn.dataset.snapshotId = snapshot.id;
    deleteBtn.textContent = '削除';

    actionsCell.appendChild(diffBtn);
    actionsCell.appendChild(restoreBtn);
    actionsCell.appendChild(deleteBtn);

    tr.appendChild(dateCell);
    tr.appendChild(nameCell);
    tr.appendChild(typeCell);
    tr.appendChild(actionsCell);
    tbody.appendChild(tr);
  }

  table.appendChild(tbody);

  container.innerHTML = '';
  container.appendChild(header);
  container.appendChild(table);

  // イベントリスナーの設定
  setupSnapshotEventListeners(container, toolId);
}

/**
 * 日付フォーマット
 * @param {string} isoString - ISO8601形式の日付文字列
 * @returns {string} フォーマットされた日付
 */
function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * イベントリスナーの設定
 * @param {HTMLElement} container - コンテナ要素
 * @param {number} toolId - ツールID
 */
function setupSnapshotEventListeners(container, toolId) {
  // 手動スナップショット作成
  const createBtn = container.querySelector('#create-snapshot-btn');
  if (createBtn) {
    createBtn.addEventListener('click', () =>
      createManualSnapshot(toolId, container),
    );
  }

  // 差分表示
  for (const btn of container.querySelectorAll('.diff-btn')) {
    btn.addEventListener('click', (e) =>
      showDiff(toolId, e.target.dataset.snapshotId),
    );
  }

  // 復元
  for (const btn of container.querySelectorAll('.restore-btn')) {
    btn.addEventListener('click', (e) =>
      restoreSnapshot(toolId, e.target.dataset.snapshotId),
    );
  }

  // 削除
  for (const btn of container.querySelectorAll('.delete-snapshot-btn')) {
    btn.addEventListener('click', (e) =>
      deleteSnapshot(toolId, e.target.dataset.snapshotId, container),
    );
  }
}

/**
 * 手動スナップショット作成
 * @param {number} toolId - ツールID
 * @param {HTMLElement} container - コンテナ要素
 */
async function createManualSnapshot(toolId, container) {
  const name = prompt('スナップショット名を入力してください（任意）:');

  try {
    const response = await fetch(`/api/tools/${toolId}/snapshots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name || null, snapshot_type: 'manual' }),
    });

    if (response.ok) {
      alert('スナップショットを作成しました。');
      fetchSnapshots(toolId, container);
    } else {
      const error = await response.json();
      alert(`エラー: ${error.detail || '作成に失敗しました'}`);
    }
  } catch (error) {
    alert('スナップショットの作成に失敗しました。');
    console.error('Error creating snapshot:', error);
  }
}

/**
 * 差分表示
 * @param {number} toolId - ツールID
 * @param {number} snapshotId - スナップショットID
 */
async function showDiff(toolId, snapshotId) {
  await loadDiff2Html();

  const diffViewer = document.getElementById('diff-viewer');
  diffViewer.classList.remove('hidden');
  diffViewer.innerHTML = '<p aria-busy="true">差分を計算中...</p>';

  try {
    const response = await fetch(
      `/api/tools/${toolId}/snapshots/${snapshotId}/diff`,
    );
    if (!response.ok) throw new Error('Failed to fetch diff');

    const data = await response.json();

    // diff.js で unified diff を生成
    const diff = Diff.createTwoFilesPatch(
      'snapshot',
      'current',
      data.old_content,
      data.new_content,
      `スナップショット #${snapshotId}`,
      '現在の内容',
    );

    // diff2html で表示
    diffViewer.innerHTML = '';
    const diff2htmlUi = new Diff2HtmlUI(diffViewer, diff, {
      drawFileList: false,
      matching: 'lines',
      outputFormat: 'side-by-side',
    });
    diff2htmlUi.draw();
    diff2htmlUi.highlightCode();
  } catch (error) {
    diffViewer.innerHTML =
      '<p style="color: var(--pico-color-red-500);">差分の取得に失敗しました。</p>';
    console.error('Error showing diff:', error);
  }
}

/**
 * スナップショットから復元
 * @param {number} toolId - ツールID
 * @param {number} snapshotId - スナップショットID
 */
async function restoreSnapshot(toolId, snapshotId) {
  if (
    !confirm(
      'このスナップショットの内容に復元しますか？\n現在の内容は自動的にスナップショットとして保存されます。',
    )
  ) {
    return;
  }

  try {
    const response = await fetch(
      `/api/tools/${toolId}/snapshots/${snapshotId}/restore`,
      {
        method: 'POST',
      },
    );

    if (response.ok) {
      alert('復元しました。ページを再読み込みします。');
      window.location.reload();
    } else {
      const error = await response.json();
      alert(`エラー: ${error.detail || '復元に失敗しました'}`);
    }
  } catch (error) {
    alert('復元に失敗しました。');
    console.error('Error restoring snapshot:', error);
  }
}

/**
 * スナップショット削除
 * @param {number} toolId - ツールID
 * @param {number} snapshotId - スナップショットID
 * @param {HTMLElement} container - コンテナ要素
 */
async function deleteSnapshot(toolId, snapshotId, container) {
  if (!confirm('このスナップショットを削除しますか？')) {
    return;
  }

  try {
    const response = await fetch(
      `/api/tools/${toolId}/snapshots/${snapshotId}`,
      {
        method: 'DELETE',
      },
    );

    if (response.ok) {
      fetchSnapshots(toolId, container);
    } else {
      alert('削除に失敗しました。');
    }
  } catch (error) {
    alert('削除に失敗しました。');
    console.error('Error deleting snapshot:', error);
  }
}

/**
 * 差分表示を閉じる
 */
// biome-ignore lint/correctness/noUnusedVariables: Called from edit.html
function closeDiffViewer() {
  const diffViewer = document.getElementById('diff-viewer');
  if (diffViewer) {
    diffViewer.classList.add('hidden');
    diffViewer.innerHTML = '';
  }
}
