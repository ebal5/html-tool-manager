/**
 * フォームバリデーション用共通モジュール
 * バックエンドと同じルールを適用
 */

const ValidationRules = {
  NAME_MIN_LENGTH: 1,
  NAME_MAX_LENGTH: 100,
  DESCRIPTION_MAX_LENGTH: 1000,
  TAG_MIN_LENGTH: 1,
  TAG_MAX_LENGTH: 50,
  TAGS_MAX_COUNT: 20,
  TOOL_TYPES: ['html', 'react'],
  // 制御文字パターン（改行・タブを除く）
  // biome-ignore lint/suspicious/noControlCharactersInRegex: 制御文字を検出するための意図的なパターン
  CONTROL_CHARS_PATTERN: /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/,
};

/**
 * 名前のバリデーション
 * @param {string} name - 名前
 * @returns {{valid: boolean, error?: string, value: string}} - バリデーション結果
 */
function validateName(name) {
  if (name === null || name === undefined) {
    return { valid: false, error: '名前は必須です', value: '' };
  }

  const trimmed = name.trim();

  if (!trimmed) {
    return { valid: false, error: '名前は空にできません', value: '' };
  }

  if (trimmed.length > ValidationRules.NAME_MAX_LENGTH) {
    return {
      valid: false,
      error: `名前は${ValidationRules.NAME_MAX_LENGTH}文字以内で入力してください`,
      value: trimmed,
    };
  }

  if (ValidationRules.CONTROL_CHARS_PATTERN.test(trimmed)) {
    return {
      valid: false,
      error: '名前に制御文字を含めることはできません',
      value: trimmed,
    };
  }

  return { valid: true, value: trimmed };
}

/**
 * 説明のバリデーション
 * @param {string|null} description - 説明
 * @returns {{valid: boolean, error?: string, value: string|null}} - バリデーション結果
 */
function validateDescription(description) {
  if (description === null || description === undefined || description === '') {
    return { valid: true, value: null };
  }

  if (description.length > ValidationRules.DESCRIPTION_MAX_LENGTH) {
    return {
      valid: false,
      error: `説明は${ValidationRules.DESCRIPTION_MAX_LENGTH}文字以内で入力してください`,
      value: description,
    };
  }

  if (ValidationRules.CONTROL_CHARS_PATTERN.test(description)) {
    return {
      valid: false,
      error: '説明に制御文字を含めることはできません',
      value: description,
    };
  }

  return { valid: true, value: description };
}

/**
 * タグのバリデーション
 * @param {string} tagsString - カンマ区切りのタグ文字列
 * @returns {{valid: boolean, error?: string, value: string[]}} - バリデーション結果
 */
function validateTags(tagsString) {
  if (!tagsString || tagsString.trim() === '') {
    return { valid: true, value: [] };
  }

  const tags = tagsString
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag) => tag !== '');

  if (tags.length > ValidationRules.TAGS_MAX_COUNT) {
    return {
      valid: false,
      error: `タグは最大${ValidationRules.TAGS_MAX_COUNT}個までです`,
      value: tags,
    };
  }

  for (const tag of tags) {
    if (
      tag.length < ValidationRules.TAG_MIN_LENGTH ||
      tag.length > ValidationRules.TAG_MAX_LENGTH
    ) {
      return {
        valid: false,
        error: `各タグは${ValidationRules.TAG_MIN_LENGTH}〜${ValidationRules.TAG_MAX_LENGTH}文字で入力してください`,
        value: tags,
      };
    }

    if (ValidationRules.CONTROL_CHARS_PATTERN.test(tag)) {
      return {
        valid: false,
        error: 'タグに制御文字を含めることはできません',
        value: tags,
      };
    }
  }

  return { valid: true, value: tags };
}

/**
 * ツールフォーム全体のバリデーション
 * @param {object} formData - フォームデータ
 * @returns {{valid: boolean, errors: string[], data: object}} - バリデーション結果
 */
// biome-ignore lint/correctness/noUnusedVariables: HTMLテンプレートから呼び出される関数
function validateToolForm(formData) {
  const errors = [];
  const data = {};

  const nameResult = validateName(formData.name);
  if (!nameResult.valid) {
    errors.push(nameResult.error);
  }
  data.name = nameResult.value;

  const descResult = validateDescription(formData.description);
  if (!descResult.valid) {
    errors.push(descResult.error);
  }
  data.description = descResult.value;

  const tagsResult = validateTags(formData.tags);
  if (!tagsResult.valid) {
    errors.push(tagsResult.error);
  }
  data.tags = tagsResult.value;

  // html_contentはそのまま渡す（サーバー側で処理）
  data.html_content = formData.html_content;

  // tool_type のバリデーション（オプショナル、自動検出を許可）
  if (
    formData.tool_type !== null &&
    formData.tool_type !== undefined &&
    formData.tool_type !== ''
  ) {
    if (!ValidationRules.TOOL_TYPES.includes(formData.tool_type)) {
      errors.push('無効なツールタイプです');
    }
  }
  data.tool_type = formData.tool_type;

  return {
    valid: errors.length === 0,
    errors: errors,
    data: data,
  };
}

/**
 * エラーメッセージを表示（XSS対策: DOM APIを使用）
 * @param {HTMLElement} messageDiv - メッセージ表示用要素
 * @param {string[]} errors - エラーメッセージの配列
 */
// biome-ignore lint/correctness/noUnusedVariables: HTMLテンプレートから呼び出される関数
function showValidationErrors(messageDiv, errors) {
  messageDiv.innerHTML = '';
  errors.forEach((error, index) => {
    messageDiv.appendChild(document.createTextNode(`❌ ${error}`));
    if (index < errors.length - 1) {
      messageDiv.appendChild(document.createElement('br'));
    }
  });
  messageDiv.style.color = 'var(--pico-color-red-500)';
}

/**
 * 入力フィールドにリアルタイムバリデーションを設定
 * @param {HTMLInputElement} input - 入力要素
 * @param {function} validator - バリデーション関数
 */
// biome-ignore lint/correctness/noUnusedVariables: HTMLテンプレートから呼び出される関数
function setupRealtimeValidation(input, validator) {
  input.addEventListener('blur', function () {
    const result = validator(this.value);
    if (!result.valid) {
      this.setAttribute('aria-invalid', 'true');
      this.setCustomValidity(result.error);
    } else {
      this.removeAttribute('aria-invalid');
      this.setCustomValidity('');
    }
  });

  input.addEventListener('input', function () {
    this.removeAttribute('aria-invalid');
    this.setCustomValidity('');
  });
}
