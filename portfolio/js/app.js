document.addEventListener('DOMContentLoaded', () => {
  let currentLang = localStorage.getItem('miniwe_lang') || 'en';

  const langBtn = document.getElementById('lang-toggle-btn');
  const yearEl = document.getElementById('year');

  if (yearEl) yearEl.textContent = new Date().getFullYear();

  function renderPage(lang) {
    const data = window.I18N_DATA[lang];
    if (!data) return;

    // 1. Static text replacement
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const keyPath = el.getAttribute('data-i18n').split('.');
      let val = data;
      keyPath.forEach(k => { val = val ? val[k] : null; });
      if (val) el.textContent = val;
    });

    // 2. Render Skills Grid
    const skillsGrid = document.getElementById('skills-grid');
    if (skillsGrid) {
      skillsGrid.innerHTML = data.skillCategories.map(cat => `
        <div class="border-2 border-brand-border bg-brand-surface p-6 shadow-brutal-sm hover:border-brand-accent transition-colors">
          <h3 class="font-mono text-lg font-bold text-brand-accent mb-4 uppercase tracking-wider">// ${cat.title}</h3>
          <ul class="space-y-2 font-mono text-sm">
            ${cat.items.map(item => `
              <li class="flex items-center gap-2">
                <span class="w-1.5 h-1.5 bg-brand-accent"></span>
                <span>${item}</span>
              </li>
            `).join('')}
          </ul>
        </div>
      `).join('');
    }

    // 3. Render Projects Grid
    const projectsContainer = document.getElementById('projects-container');
    if (projectsContainer) {
      projectsContainer.innerHTML = data.projectsList.map((proj, idx) => `
        <div class="border-2 border-brand-border bg-brand-surface p-6 md:p-8 hover:border-brand-accent transition-all group">
          <div class="flex flex-wrap justify-between items-start gap-2 mb-4 font-mono text-xs text-brand-muted">
            <span class="text-brand-accent">[PROJECT 0${idx + 1}]</span>
            <span>${proj.category}</span>
          </div>

          <h3 class="text-2xl sm:text-3xl font-bold mb-3 group-hover:text-brand-accent transition-colors">
            ${proj.title}
          </h3>

          <p class="text-brand-muted text-base mb-6 max-w-3xl leading-relaxed">
            ${proj.description}
          </p>

          <div class="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-brand-border">
            <div class="flex flex-wrap gap-2">
              ${proj.tags.map(tag => `
                <span class="text-xs font-mono border border-brand-border px-2 py-1 bg-brand-black text-brand-lightText">
                  ${tag}
                </span>
              `).join('')}
            </div>

            <a href="${proj.link}" target="_blank" rel="noopener" class="font-mono text-xs font-bold text-brand-accent hover:underline flex items-center gap-1">
              EXPLORE ↗
            </a>
          </div>
        </div>
      `).join('');
    }

    // Toggle button state
    if (langBtn) {
      langBtn.textContent = lang === 'en' ? 'EN / RU' : 'RU / EN';
    }
  }

  // Initial Load
  renderPage(currentLang);

  // Language Switch Listener
  if (langBtn) {
    langBtn.addEventListener('click', () => {
      currentLang = currentLang === 'en' ? 'ru' : 'en';
      localStorage.setItem('miniwe_lang', currentLang);
      renderPage(currentLang);
    });
  }
});