/**
 * Backup management page JavaScript
 */
document.addEventListener('DOMContentLoaded', () => {
  const createBackupBtn = document.getElementById('create-backup-btn');
  const container = document.getElementById('backup-list-container');
  const messageContainer = document.getElementById('message-container');

  /**
   * Show a message to the user
   * @param {string} message - The message to display
   * @param {string} type - Message type: 'success' or 'error'
   */
  function showMessage(message, type) {
    messageContainer.style.display = 'block';
    messageContainer.textContent = message;
    messageContainer.style.color =
      type === 'success'
        ? 'var(--pico-color-green-500)'
        : 'var(--pico-color-red-500)';

    // Auto-hide after 5 seconds
    setTimeout(() => {
      messageContainer.style.display = 'none';
    }, 5000);
  }

  /**
   * Format date to locale string
   * @param {string} isoString - ISO date string
   * @returns {string} Formatted date string
   */
  function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('ja-JP', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  /**
   * Fetch and display backup list
   */
  async function fetchBackups() {
    container.innerHTML = '<p aria-busy="true">読み込み中...</p>';

    try {
      const response = await fetch('/api/backup/');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      renderBackupList(data.backups);
    } catch (error) {
      console.error('Failed to fetch backups:', error);
      container.innerHTML = '<p>バックアップ一覧の取得に失敗しました。</p>';
    }
  }

  /**
   * Render backup list as a table
   * @param {Array} backups - Array of backup objects
   */
  function renderBackupList(backups) {
    if (backups.length === 0) {
      container.innerHTML = '<p>バックアップはありません。</p>';
      return;
    }

    const table = document.createElement('table');
    table.innerHTML = `
            <thead>
                <tr>
                    <th>ファイル名</th>
                    <th>作成日時</th>
                    <th>サイズ</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;

    const tbody = table.querySelector('tbody');

    for (const backup of backups) {
      const tr = document.createElement('tr');

      // Filename cell
      const filenameTd = document.createElement('td');
      filenameTd.textContent = backup.filename;
      tr.appendChild(filenameTd);

      // Created at cell
      const createdAtTd = document.createElement('td');
      createdAtTd.textContent = formatDate(backup.created_at);
      tr.appendChild(createdAtTd);

      // Size cell
      const sizeTd = document.createElement('td');
      sizeTd.textContent = backup.size_human;
      tr.appendChild(sizeTd);

      // Actions cell
      const actionsTd = document.createElement('td');

      const restoreBtn = document.createElement('button');
      restoreBtn.className = 'secondary outline';
      restoreBtn.textContent = '復元';
      restoreBtn.dataset.filename = backup.filename;
      restoreBtn.addEventListener('click', () =>
        handleRestore(backup.filename, restoreBtn),
      );

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'contrast outline';
      deleteBtn.textContent = '削除';
      deleteBtn.style.marginLeft = '0.5rem';
      deleteBtn.dataset.filename = backup.filename;
      deleteBtn.addEventListener('click', () =>
        handleDelete(backup.filename, deleteBtn),
      );

      actionsTd.appendChild(restoreBtn);
      actionsTd.appendChild(deleteBtn);
      tr.appendChild(actionsTd);

      tbody.appendChild(tr);
    }

    container.innerHTML = '';
    container.appendChild(table);
  }

  /**
   * Handle backup creation
   */
  async function handleCreateBackup() {
    createBackupBtn.setAttribute('aria-busy', 'true');
    createBackupBtn.disabled = true;

    try {
      const response = await fetch('/api/backup/', {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Backup creation failed');
      }

      const data = await response.json();
      showMessage(
        `バックアップを作成しました: ${data.backup.filename}`,
        'success',
      );
      fetchBackups();
    } catch (error) {
      console.error('Failed to create backup:', error);
      showMessage(
        `バックアップの作成に失敗しました: ${error.message}`,
        'error',
      );
    } finally {
      createBackupBtn.removeAttribute('aria-busy');
      createBackupBtn.disabled = false;
    }
  }

  /**
   * Handle backup restoration
   * @param {string} filename - Backup filename to restore
   * @param {HTMLButtonElement} button - The restore button element
   */
  async function handleRestore(filename, button) {
    const confirmed = confirm(
      `本当に「${filename}」から復元しますか？\n\n` +
        '注意: 現在のデータベースは上書きされます。\n' +
        '復元後、アプリケーションの再起動が必要になる場合があります。',
    );

    if (!confirmed) {
      return;
    }

    button.setAttribute('aria-busy', 'true');
    button.disabled = true;

    try {
      const response = await fetch(`/api/backup/restore/${filename}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Restoration failed');
      }

      showMessage(
        `復元が完了しました。アプリケーションの再起動を推奨します。`,
        'success',
      );
    } catch (error) {
      console.error('Failed to restore backup:', error);
      showMessage(`復元に失敗しました: ${error.message}`, 'error');
    } finally {
      button.removeAttribute('aria-busy');
      button.disabled = false;
    }
  }

  /**
   * Handle backup deletion
   * @param {string} filename - Backup filename to delete
   * @param {HTMLButtonElement} button - The delete button element
   */
  async function handleDelete(filename, button) {
    const confirmed = confirm(
      `本当に「${filename}」を削除しますか？\n\nこの操作は取り消せません。`,
    );

    if (!confirmed) {
      return;
    }

    button.setAttribute('aria-busy', 'true');
    button.disabled = true;

    try {
      const response = await fetch(`/api/backup/${filename}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Deletion failed');
      }

      showMessage(`バックアップ「${filename}」を削除しました。`, 'success');
      fetchBackups();
    } catch (error) {
      console.error('Failed to delete backup:', error);
      showMessage(`削除に失敗しました: ${error.message}`, 'error');
    } finally {
      button.removeAttribute('aria-busy');
      button.disabled = false;
    }
  }

  // Event listeners
  if (createBackupBtn) {
    createBackupBtn.addEventListener('click', handleCreateBackup);
  }

  // Initial load
  fetchBackups();
});
