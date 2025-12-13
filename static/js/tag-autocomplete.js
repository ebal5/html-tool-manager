/**
 * タグオートコンプリート機能
 */

// 各input要素ごとのデバウンスタイマーを管理
const debounceTimers = new WeakMap();

/**
 * タグ候補を取得してdatalistを更新
 * @param {string} query - 検索クエリ
 * @param {HTMLDataListElement} datalist - 更新するdatalist要素
 */
async function fetchTagSuggestions(query, datalist) {
  try {
    const response = await fetch(
      `/api/tools/tags/suggest?q=${encodeURIComponent(query)}`,
    );
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const tags = await response.json();

    // datalistの内容を更新
    datalist.innerHTML = '';
    for (const tag of tags) {
      const option = document.createElement('option');
      option.value = tag;
      datalist.appendChild(option);
    }
  } catch (error) {
    console.error('Error fetching tag suggestions:', error);
  }
}

/**
 * タグ入力フィールドにオートコンプリートを設定
 * @param {HTMLInputElement} input - タグ入力フィールド
 * @param {string} datalistId - datalist要素のID
 */
// biome-ignore lint/correctness/noUnusedVariables: HTMLテンプレートから呼び出される
function setupTagAutocomplete(input, datalistId) {
  if (!input) return;

  // datalist要素を作成（まだ存在しない場合）
  let datalist = document.getElementById(datalistId);
  if (!datalist) {
    datalist = document.createElement('datalist');
    datalist.id = datalistId;
    input.parentNode.insertBefore(datalist, input.nextSibling);
  }

  // inputにdatalistを関連付け
  input.setAttribute('list', datalistId);

  // 初期候補を読み込み
  fetchTagSuggestions('', datalist);

  input.addEventListener('input', () => {
    const currentTimer = debounceTimers.get(input);
    if (currentTimer) {
      clearTimeout(currentTimer);
    }

    const value = input.value;

    // カンマで区切って最後のタグを取得
    const tags = value.split(',');
    const lastTag = tags[tags.length - 1].trim();

    // デバウンス後に候補を取得
    const newTimer = setTimeout(() => {
      fetchTagSuggestions(lastTag, datalist);
    }, 300);
    debounceTimers.set(input, newTimer);
  });
}
