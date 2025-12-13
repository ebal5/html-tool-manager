/**
 * Template Library Gallery
 * Handles fetching, filtering, and adding templates as tools.
 */

document.addEventListener('DOMContentLoaded', () => {
  const gallery = document.getElementById('templates-gallery');
  const categoryFilter = document.querySelector('.category-filter');
  let templatesData = null;
  let currentCategory = 'all';

  /**
   * Fetch templates from API
   */
  async function fetchTemplates() {
    try {
      const response = await fetch('/api/templates/');
      if (!response.ok) {
        throw new Error('Failed to fetch templates');
      }
      templatesData = await response.json();
      renderCategoryButtons();
      renderTemplates();
    } catch (error) {
      gallery.innerHTML =
        '<p style="color: var(--pico-color-red-550);">テンプレートの読み込みに失敗しました。</p>';
      console.error('Error fetching templates:', error);
    }
  }

  /**
   * Render category filter buttons
   */
  function renderCategoryButtons() {
    const categories = templatesData.categories;
    for (const [key, cat] of Object.entries(categories)) {
      const btn = document.createElement('button');
      btn.className = 'category-btn';
      btn.dataset.category = key;
      btn.textContent = cat.name;
      btn.addEventListener('click', () => filterByCategory(key));
      categoryFilter.appendChild(btn);
    }
  }

  /**
   * Filter templates by category
   * @param {string} category - Category key or 'all'
   */
  function filterByCategory(category) {
    currentCategory = category;
    // Update active state of buttons
    categoryFilter.querySelectorAll('.category-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.category === category);
    });
    renderTemplates();
  }

  /**
   * Render template cards
   */
  function renderTemplates() {
    const templates =
      currentCategory === 'all'
        ? templatesData.templates
        : templatesData.templates.filter((t) => t.category === currentCategory);

    gallery.innerHTML = '';

    if (templates.length === 0) {
      gallery.innerHTML = '<p>該当するテンプレートがありません。</p>';
      return;
    }

    for (const template of templates) {
      const card = createTemplateCard(template);
      gallery.appendChild(card);
    }
  }

  /**
   * Create a template card element
   * @param {Object} template - Template data
   * @returns {HTMLElement} Card element
   */
  function createTemplateCard(template) {
    const card = document.createElement('article');
    card.className = 'template-card';
    card.dataset.category = template.category;

    // Category name
    const categoryName =
      templatesData.categories[template.category]?.name || template.category;

    // Category badge
    const categoryBadge = document.createElement('span');
    categoryBadge.className = 'category-badge';
    categoryBadge.textContent = categoryName;

    // Title
    const title = document.createElement('h3');
    title.textContent = template.name;

    // Description
    const desc = document.createElement('p');
    desc.textContent = template.description;

    // Tags
    const tagsDiv = document.createElement('div');
    tagsDiv.className = 'tags';
    for (const tag of template.tags) {
      const code = document.createElement('code');
      code.textContent = tag;
      tagsDiv.appendChild(code);
      tagsDiv.appendChild(document.createTextNode(' '));
    }

    // Add button
    const addBtn = document.createElement('button');
    addBtn.textContent = '追加';
    addBtn.addEventListener('click', () => addTemplate(template.id, addBtn));

    card.appendChild(categoryBadge);
    card.appendChild(title);
    card.appendChild(desc);
    card.appendChild(tagsDiv);
    card.appendChild(addBtn);

    return card;
  }

  /**
   * Add a template as a new tool
   * @param {string} templateId - Template ID
   * @param {HTMLElement} button - Button element
   */
  async function addTemplate(templateId, button) {
    button.setAttribute('aria-busy', 'true');
    button.disabled = true;

    try {
      const response = await fetch(`/api/templates/${templateId}/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add template');
      }

      // Success
      button.removeAttribute('aria-busy');
      button.textContent = '追加しました!';
      button.classList.add('success');
      button.classList.remove('primary');

      // Reset after delay
      setTimeout(() => {
        button.textContent = '追加';
        button.classList.remove('success');
        button.disabled = false;
      }, 3000);
    } catch (error) {
      button.removeAttribute('aria-busy');
      button.textContent = 'エラー';
      button.disabled = false;
      console.error('Error adding template:', error);
      alert(`追加に失敗しました: ${error.message}`);

      setTimeout(() => {
        button.textContent = '追加';
      }, 2000);
    }
  }

  // Initialize
  fetchTemplates();
});
