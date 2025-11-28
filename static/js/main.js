document.addEventListener('DOMContentLoaded', () => {
    const searchBox = document.getElementById('search-box');
    const sortSelect = document.getElementById('sort-select');
    const container = document.getElementById('tool-list-container');
    const exportSelectedBtn = document.getElementById('export-selected-btn');
    const importFileInput = document.getElementById('import-file-input');
    const importBtn = document.getElementById('import-btn');
    const toggleToolOperationsBtn = document.getElementById('toggle-tool-operations');
    const toolOperationsContainer = document.getElementById('tool-operations-container');

    let debounceTimer;

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

            const table = document.createElement('table');
            table.innerHTML = `
                <thead>
                    <tr>
                        <th class="checkbox-column hidden"><input type="checkbox" id="select-all-tools"></th>
                        <th>名前</th>
                        <th>説明</th>
                        <th>タグ</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody></tbody>
            `;
            const tbody = table.querySelector('tbody');

            const isOperationsVisible = !toolOperationsContainer.classList.contains('hidden');

            tools.forEach(tool => {
                const tr = document.createElement('tr');
                tr.dataset.toolId = tool.id; // エクスポート用にIDを保持

                const checkboxCell = document.createElement('td');
                checkboxCell.classList.add('checkbox-column');
                if (!isOperationsVisible) { // 初期状態では非表示
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
                            tagsCell.appendChild(document.createTextNode(' ')); // for spacing
                        }
                    });
                }

                const actionsCell = document.createElement('td');
                actionsCell.innerHTML = `<div class="action-grid">
                    <a href="/tools/view/${tool.id}" role="button" class="secondary outline">使用</a>
                    <details class="dropdown">
                        <summary role="button" class="contrast outline">⋮</summary>
                        <ul style="position: absolute; z-index: 1;">
                            <li><a href="/tools/edit/${tool.id}">編集</a></li>
                            <li><a href="#" onclick="event.preventDefault(); deleteTool(${tool.id}, this)">削除</a></li>
                        </ul>
                    </details>
                </div>`;

                tr.appendChild(checkboxCell);
                tr.appendChild(nameCell);
                tr.appendChild(descCell);
                tr.appendChild(tagsCell);
                tr.appendChild(actionsCell);

                tbody.appendChild(tr);
            });

            container.innerHTML = '';
            container.appendChild(table);

            // 「すべて選択」チェックボックスのイベントリスナー設定
            const selectAllCheckbox = document.getElementById('select-all-tools');
            if (selectAllCheckbox) {
                selectAllCheckbox.addEventListener('change', (event) => {
                    document.querySelectorAll('.tool-checkbox').forEach(cb => {
                        cb.checked = event.target.checked;
                    });
                });
            }

        } catch (error) {
            container.innerHTML = `<p style="color: var(--pico-color-red-500);">ツールの読み込みに失敗しました。</p>`;
            console.error('Error fetching tools:', error);
        }
    }

    searchBox.addEventListener('input', () => {
        clearTimeout(debounceTimer);

        const query = searchBox.value.trim();
        if (query.endsWith(':')) {
            return;
        }

        debounceTimer = setTimeout(fetchTools, 300);
    });

    sortSelect.addEventListener('change', fetchTools);

    // Initial load
    fetchTools();

    // --- ツール操作UIの表示/非表示を切り替える ---
    toggleToolOperationsBtn.addEventListener('click', () => {
        toolOperationsContainer.classList.toggle('hidden');
        document.querySelectorAll('.checkbox-column').forEach(el => {
            el.classList.toggle('hidden');
        });
    });


    // --- ツール削除機能 ---
    window.deleteTool = function(toolId, buttonElement) {
        if (confirm(`ツールID: ${toolId} を削除しますか？`)) {
            buttonElement.setAttribute('aria-busy', 'true');
            fetch(`/api/tools/${toolId}`, {
                method: 'DELETE',
            })
            .then(response => {
                if (response.ok) {
                    const row = buttonElement.closest('tr');
                    row.parentNode.removeChild(row);
                    fetchTools(); // ツールリストをリロード
                } else {
                    alert('ツールの削除に失敗しました。');
                    buttonElement.removeAttribute('aria-busy');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('削除中にエラーが発生しました。');
                buttonElement.removeAttribute('aria-busy');
            });
        }
    };

    // --- ツールエクスポート機能 ---
    exportSelectedBtn.addEventListener('click', async () => {
        const selectedToolIds = Array.from(document.querySelectorAll('.tool-checkbox:checked'))
            .map(checkbox => checkbox.closest('tr').dataset.toolId)
            .filter(id => id); // 無効なIDを除外

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
                alert(`${selectedToolIds.length}個のツールがエクスポートされました。`);
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

    // --- ツールインポート機能 ---
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
                alert(`${result.imported_count}個のツールが正常にインポートされました。`);
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
});