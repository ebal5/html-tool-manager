document.addEventListener('DOMContentLoaded', () => {
  const searchBox = document.getElementById('search-box');
  const sortSelect = document.getElementById('sort-select');
  const container = document.getElementById('tool-list-container');
  const exportSelectedBtn = document.getElementById('export-selected-btn');
  const importFileInput = document.getElementById('import-file-input');
  const importBtn = document.getElementById('import-btn');
  const toggleToolOperationsBtn = document.getElementById(
    'toggle-tool-operations',
  );
  const toolOperationsContainer = document.getElementById(
    'tool-operations-container',
  );

  // View switcher elements
  const viewListBtn = document.getElementById('view-list');
  const viewCardBtn = document.getElementById('view-card');
  const viewGridBtn = document.getElementById('view-grid');
  // Cache view buttons array for performance (avoid querySelectorAll on each update)
  const viewButtons = [viewListBtn, viewCardBtn, viewGridBtn].filter(Boolean);
  const viewButtonMap = {
    list: viewListBtn,
    card: viewCardBtn,
    grid: viewGridBtn,
  };

  let debounceTimer;
  let currentView = 'list';

  // localStorage helper with error handling
  function getStorageItem(key, defaultValue) {
    try {
      return localStorage.getItem(key) ?? defaultValue;
    } catch {
      console.warn('localStorage is not available');
      return defaultValue;
    }
  }

  function setStorageItem(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      console.warn('localStorage is not available');
    }
  }

  // Initialize view from localStorage
  currentView = getStorageItem('toolViewMode', 'list');

  // --- View mode functions ---
  function updateViewButtons() {
    // Use cached button references instead of querySelectorAll
    for (const btn of viewButtons) {
      btn.classList.remove('active');
      btn.setAttribute('aria-pressed', 'false');
    }

    const activeBtn = viewButtonMap[currentView];
    if (activeBtn) {
      activeBtn.classList.add('active');
      activeBtn.setAttribute('aria-pressed', 'true');
    }
  }

  function setView(view) {
    currentView = view;
    setStorageItem('toolViewMode', view);
    updateViewButtons();
    fetchTools();
  }

  // Initialize view buttons
  if (viewListBtn) {
    viewListBtn.addEventListener('click', () => setView('list'));
  }
  if (viewCardBtn) {
    viewCardBtn.addEventListener('click', () => setView('card'));
  }
  if (viewGridBtn) {
    viewGridBtn.addEventListener('click', () => setView('grid'));
  }

  // Set initial view state
  updateViewButtons();

  // --- ツール一覧の取得と表示 ---
  async function fetchTools() {
    container.innerHTML = '<p aria-busy="true">ツールを読み込み中...</p>';
    const query = searchBox.value;
    const sort = sortSelect.value;

    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (sort) params.append('sort', sort);

    try {
      const response = await fetch(`/api/tools/?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const tools = await response.json();

      if (tools.length === 0) {
        container.innerHTML = '<p>ツールが見つかりませんでした。</p>';
        return;
      }

      container.innerHTML = '';

      // ビュー描画（エラー時はリストビューにフォールバック）
      try {
        if (currentView === 'list') {
          renderListView(tools);
        } else if (currentView === 'card') {
          renderCardView(tools);
        } else if (currentView === 'grid') {
          renderGridView(tools);
        }
      } catch (renderError) {
        console.error('Error rendering view:', renderError);
        container.innerHTML =
          '<p class="error-message">表示エラーが発生しました。リストビューに切り替えます。</p>';
        // フォールバック：リストビューに戻す
        currentView = 'list';
        setStorageItem('toolViewMode', 'list');
        updateViewButtons();
        try {
          renderListView(tools);
        } catch (fallbackError) {
          console.error('Fallback render also failed:', fallbackError);
        }
      }

      // 削除ボタンのイベント委譲（インラインハンドラを避けてCSP準拠）
      container.addEventListener('click', handleDeleteClick);
    } catch (error) {
      container.innerHTML =
        '<p class="error-message">ツールの読み込みに失敗しました。</p>';
      console.error('Error fetching tools:', error);
    }
  }

  // --- List View Renderer ---
  function renderListView(tools) {
    const table = document.createElement('table');
    table.innerHTML = `
                <thead>
                    <tr>
                        <th class="checkbox-column hidden"><input type="checkbox" id="select-all-tools"></th>
                        <th>名前</th>
                        <th>説明</th>
                        <th>タグ</th>
                        <th>タイプ</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody></tbody>
            `;
    const tbody = table.querySelector('tbody');

    const isOperationsVisible =
      !toolOperationsContainer.classList.contains('hidden');

    tools.forEach((tool) => {
      const tr = document.createElement('tr');
      tr.dataset.toolId = tool.id;

      const checkboxCell = document.createElement('td');
      checkboxCell.classList.add('checkbox-column');
      if (!isOperationsVisible) {
        checkboxCell.classList.add('hidden');
      }
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'tool-checkbox';
      checkboxCell.appendChild(checkbox);

      const nameCell = document.createElement('td');
      nameCell.textContent = tool.name;

      const descCell = document.createElement('td');
      descCell.textContent = tool.description || '';

      const tagsCell = document.createElement('td');
      if (tool.tags && tool.tags.length > 0) {
        tool.tags.forEach((tag, index) => {
          const code = document.createElement('code');
          code.textContent = tag;
          tagsCell.appendChild(code);
          if (index < tool.tags.length - 1) {
            tagsCell.appendChild(document.createTextNode(' '));
          }
        });
      }

      const typeCell = document.createElement('td');
      typeCell.appendChild(createTypeBadge(tool.tool_type));

      const actionsCell = document.createElement('td');
      actionsCell.appendChild(createActions(tool));

      tr.appendChild(checkboxCell);
      tr.appendChild(nameCell);
      tr.appendChild(descCell);
      tr.appendChild(tagsCell);
      tr.appendChild(typeCell);
      tr.appendChild(actionsCell);

      tbody.appendChild(tr);
    });

    container.appendChild(table);

    // Setup select-all event
    setupSelectAllHandler();
  }

  // --- Create select-all header (shared by card/grid views) ---
  function createSelectAllHeader(isOperationsVisible) {
    const selectAllHeader = document.createElement('div');
    selectAllHeader.className = 'select-all-header';
    if (!isOperationsVisible) {
      selectAllHeader.classList.add('hidden');
    }
    const selectAllCheckbox = document.createElement('input');
    selectAllCheckbox.type = 'checkbox';
    selectAllCheckbox.id = 'select-all-tools';
    const selectAllLabel = document.createElement('label');
    selectAllLabel.htmlFor = 'select-all-tools';
    selectAllLabel.textContent = 'すべて選択';
    selectAllHeader.appendChild(selectAllCheckbox);
    selectAllHeader.appendChild(selectAllLabel);
    return selectAllHeader;
  }

  // --- Card View Renderer ---
  function renderCardView(tools) {
    const isOperationsVisible =
      !toolOperationsContainer.classList.contains('hidden');

    container.appendChild(createSelectAllHeader(isOperationsVisible));

    const cardContainer = document.createElement('div');
    cardContainer.className = 'tools-card-view';

    tools.forEach((tool) => {
      const card = document.createElement('div');
      card.className = 'tool-card';
      card.dataset.toolId = tool.id;

      const header = document.createElement('div');
      header.className = 'tool-card-header';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'tool-checkbox tool-card-checkbox';
      if (!isOperationsVisible) {
        checkbox.classList.add('hidden');
      }
      header.appendChild(checkbox);

      const title = document.createElement('h3');
      title.className = 'tool-card-title';
      title.textContent = tool.name;
      header.appendChild(title);

      const thumbnail = document.createElement('div');
      thumbnail.className = 'tool-card-thumbnail';
      thumbnail.textContent = '🛠️';

      const description = document.createElement('p');
      description.className = 'tool-card-description';
      description.textContent = tool.description || 'No description';

      const tagsDiv = document.createElement('div');
      tagsDiv.className = 'tool-card-tags';
      if (tool.tags && tool.tags.length > 0) {
        tool.tags.forEach((tag) => {
          const code = document.createElement('code');
          code.textContent = tag;
          tagsDiv.appendChild(code);
        });
      }

      const typeDiv = document.createElement('div');
      typeDiv.className = 'tool-card-type';
      typeDiv.appendChild(createTypeBadge(tool.tool_type));

      const actions = document.createElement('div');
      actions.className = 'tool-card-actions';
      actions.appendChild(createActions(tool));

      card.appendChild(header);
      card.appendChild(thumbnail);
      card.appendChild(description);
      card.appendChild(tagsDiv);
      card.appendChild(typeDiv);
      card.appendChild(actions);

      cardContainer.appendChild(card);
    });

    container.appendChild(cardContainer);

    // Setup select-all event
    setupSelectAllHandler();
  }

  // --- Grid View Renderer ---
  function renderGridView(tools) {
    const isOperationsVisible =
      !toolOperationsContainer.classList.contains('hidden');

    container.appendChild(createSelectAllHeader(isOperationsVisible));

    const gridContainer = document.createElement('div');
    gridContainer.className = 'tools-grid-view';

    tools.forEach((tool) => {
      const gridItem = document.createElement('div');
      gridItem.className = 'tool-grid-item';
      gridItem.dataset.toolId = tool.id;
      gridItem.setAttribute('tabindex', '0');
      gridItem.setAttribute('role', 'button');
      gridItem.setAttribute('aria-label', `${tool.name}を表示`);

      const header = document.createElement('div');
      header.className = 'tool-grid-header';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'tool-checkbox tool-grid-checkbox';
      if (!isOperationsVisible) {
        checkbox.classList.add('hidden');
      }
      header.appendChild(checkbox);

      const title = document.createElement('h4');
      title.className = 'tool-grid-title';
      title.textContent = tool.name;
      header.appendChild(title);

      const thumbnail = document.createElement('div');
      thumbnail.className = 'tool-grid-thumbnail';
      thumbnail.textContent = '🛠️';

      const metaDiv = document.createElement('div');
      metaDiv.className = 'tool-grid-meta';

      const tagsDiv = document.createElement('div');
      tagsDiv.className = 'tool-grid-tags';
      if (tool.tags && tool.tags.length > 0) {
        tool.tags.forEach((tag) => {
          const code = document.createElement('code');
          code.textContent = tag;
          tagsDiv.appendChild(code);
        });
      }

      metaDiv.appendChild(createTypeBadge(tool.tool_type));
      metaDiv.appendChild(tagsDiv);

      gridItem.appendChild(header);
      gridItem.appendChild(thumbnail);
      gridItem.appendChild(metaDiv);

      gridContainer.appendChild(gridItem);
    });

    container.appendChild(gridContainer);

    // Setup select-all and grid click/keyboard events (event delegation)
    setupSelectAllHandler();
    gridContainer.addEventListener('click', handleGridItemClick);
    gridContainer.addEventListener('keydown', handleGridItemKeydown);
  }

  // --- Grid item click handler (event delegation) ---
  function handleGridItemClick(e) {
    const gridItem = e.target.closest('.tool-grid-item');
    if (!gridItem) return;

    // Don't navigate if clicking checkbox or interactive elements
    if (
      e.target.classList.contains('tool-checkbox') ||
      e.target.closest('button') ||
      e.target.closest('a')
    ) {
      return;
    }

    navigateToTool(gridItem);
  }

  // --- Grid item keyboard handler (event delegation) ---
  function handleGridItemKeydown(e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;

    const gridItem = e.target.closest('.tool-grid-item');
    if (!gridItem) return;

    // Don't navigate if focus is on checkbox
    if (e.target.classList.contains('tool-checkbox')) {
      return;
    }

    e.preventDefault();
    navigateToTool(gridItem);
  }

  // --- Navigate to tool view ---
  function navigateToTool(gridItem) {
    const toolId = gridItem.dataset.toolId;
    if (toolId) {
      window.location.href = `/tools/view/${toolId}`;
    }
  }

  // --- Setup select-all checkbox handler ---
  function setupSelectAllHandler() {
    const selectAllCheckbox = document.getElementById('select-all-tools');
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener('change', (event) => {
        document.querySelectorAll('.tool-checkbox').forEach((cb) => {
          cb.checked = event.target.checked;
        });
      });
    }
  }

  // --- Helper functions ---
  function createTypeBadge(toolType) {
    const typeBadge = document.createElement('code');
    const type = toolType || 'html';
    if (type === 'react') {
      typeBadge.textContent = 'React';
      typeBadge.style.backgroundColor = '#61DAFB';
      typeBadge.style.color = '#000';
    } else {
      typeBadge.textContent = 'HTML';
      typeBadge.style.backgroundColor = '#E34C26';
      typeBadge.style.color = '#fff';
    }
    typeBadge.style.padding = '0.25rem 0.5rem';
    typeBadge.style.borderRadius = '0.25rem';
    typeBadge.style.fontSize = '0.875rem';
    return typeBadge;
  }

  function createActions(tool) {
    const actionDiv = document.createElement('div');
    actionDiv.className = 'action-grid';

    const viewLink = document.createElement('a');
    viewLink.href = `/tools/view/${tool.id}`;
    viewLink.setAttribute('role', 'button');
    viewLink.className = 'secondary outline';
    viewLink.textContent = '使用';

    const dropdown = document.createElement('details');
    dropdown.className = 'dropdown';

    const summary = document.createElement('summary');
    summary.setAttribute('role', 'button');
    summary.className = 'contrast outline';
    summary.textContent = '⋮';

    const ul = document.createElement('ul');
    ul.style.position = 'absolute';
    ul.style.zIndex = '1';

    const editLi = document.createElement('li');
    const editLink = document.createElement('a');
    editLink.href = `/tools/edit/${tool.id}`;
    editLink.textContent = '編集';
    editLi.appendChild(editLink);

    const deleteLi = document.createElement('li');
    const deleteLink = document.createElement('a');
    deleteLink.href = '#';
    deleteLink.className = 'delete-tool-btn';
    deleteLink.dataset.toolId = tool.id;
    deleteLink.textContent = '削除';
    deleteLi.appendChild(deleteLink);

    ul.appendChild(editLi);
    ul.appendChild(deleteLi);
    dropdown.appendChild(summary);
    dropdown.appendChild(ul);
    actionDiv.appendChild(viewLink);
    actionDiv.appendChild(dropdown);

    return actionDiv;
  }

  // 検索ボックスがあるページでのみイベントリスナーを登録
  if (searchBox) {
    searchBox.addEventListener('input', () => {
      clearTimeout(debounceTimer);

      const query = searchBox.value.trim();
      if (query.endsWith(':')) {
        return;
      }

      debounceTimer = setTimeout(fetchTools, 300);
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener('change', fetchTools);
  }

  // Initial load（コンテナがあるページでのみ）
  if (container) {
    fetchTools();
  }

  // --- ツール操作UIの表示/非表示を切り替える ---
  if (toggleToolOperationsBtn) {
    toggleToolOperationsBtn.addEventListener('click', () => {
      toolOperationsContainer.classList.toggle('hidden');
      // Update checkboxes and select-all header for all view modes
      document.querySelectorAll('.checkbox-column').forEach((el) => {
        el.classList.toggle('hidden');
      });
      document
        .querySelectorAll('.tool-card-checkbox, .tool-grid-checkbox')
        .forEach((el) => {
          el.classList.toggle('hidden');
        });
      document.querySelectorAll('.select-all-header').forEach((el) => {
        el.classList.toggle('hidden');
      });
    });
  }

  // --- ツール削除機能（イベント委譲ハンドラ） ---
  function handleDeleteClick(event) {
    const deleteBtn = event.target.closest('.delete-tool-btn');
    if (!deleteBtn) return;

    event.preventDefault();
    const toolId = deleteBtn.dataset.toolId;
    if (!toolId) return;

    if (confirm(`ツールID: ${toolId} を削除しますか？`)) {
      deleteBtn.setAttribute('aria-busy', 'true');
      fetch(`/api/tools/${toolId}`, {
        method: 'DELETE',
      })
        .then((response) => {
          if (response.ok) {
            const row = deleteBtn.closest('tr');
            row.parentNode.removeChild(row);
            fetchTools(); // ツールリストをリロード
          } else {
            alert('ツールの削除に失敗しました。');
            deleteBtn.removeAttribute('aria-busy');
          }
        })
        .catch((error) => {
          console.error('Error:', error);
          alert('削除中にエラーが発生しました。');
          deleteBtn.removeAttribute('aria-busy');
        });
    }
  }

  // --- ツールエクスポート機能 ---
  if (exportSelectedBtn) {
    exportSelectedBtn.addEventListener('click', async () => {
      const selectedToolIds = Array.from(
        document.querySelectorAll('.tool-checkbox:checked'),
      )
        .map((checkbox) => checkbox.closest('[data-tool-id]')?.dataset.toolId)
        .filter((id) => id); // 無効なIDを除外

      if (selectedToolIds.length === 0) {
        alert('エクスポートするツールを選択してください。');
        return;
      }

      exportSelectedBtn.setAttribute('aria-busy', 'true');
      try {
        const response = await fetch('/api/tools/export', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ tool_ids: selectedToolIds }),
        });

        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.style.display = 'none';
          a.href = url;
          a.download = 'tools-export.pack';
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          alert(
            `${selectedToolIds.length}個のツールがエクスポートされました。`,
          );
        } else {
          const errorText = await response.text();
          alert(`エクスポート失敗: ${response.status} - ${errorText}`);
        }
      } catch (error) {
        console.error('エクスポートエラー:', error);
        alert('エクスポート中にエラーが発生しました。');
      } finally {
        exportSelectedBtn.removeAttribute('aria-busy');
      }
    });
  }

  // --- ツールインポート機能 ---
  if (importBtn) {
    importBtn.addEventListener('click', async () => {
      const file = importFileInput.files[0];
      if (!file) {
        alert('インポートするファイルを選択してください。');
        return;
      }

      importBtn.setAttribute('aria-busy', 'true');
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('/api/tools/import', {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
          alert(
            `${result.imported_count}個のツールが正常にインポートされました。`,
          );
          fetchTools(); // リストをリロード
        } else {
          const errorText = await response.text();
          alert(`インポート失敗: ${response.status} - ${errorText}`);
        }
      } catch (error) {
        console.error('インポートエラー:', error);
        alert('インポート中にエラーが発生しました。');
      } finally {
        importBtn.removeAttribute('aria-busy');
        importFileInput.value = ''; // ファイル選択をリセット
      }
    });
  }
});
