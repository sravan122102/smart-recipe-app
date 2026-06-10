/**
 * ============================================================
 *  Smart Recipe Suggestion System — Client-Side Application
 * ============================================================
 *  Three-screen SPA:
 *    1. Ingredient Input   (#input-screen)
 *    2. Recipe Results      (#results-screen)
 *    3. Recipe Detail       (#detail-screen)
 * ============================================================
 */

document.addEventListener('DOMContentLoaded', () => {

  // ─── State ──────────────────────────────────────────────
  let allIngredients = [];
  let selectedIngredients = [];
  let highlightIndex = -1;
  let currentResults = [];

  // ─── DOM References ─────────────────────────────────────
  const inputScreen         = document.getElementById('input-screen');
  const resultsScreen       = document.getElementById('results-screen');
  const detailScreen        = document.getElementById('detail-screen');
  const ingredientInput     = document.getElementById('ingredient-input');
  const autocompleteDropdown = document.getElementById('autocomplete-dropdown');
  const ingredientTags      = document.getElementById('ingredient-tags');
  const ingredientCount     = document.getElementById('ingredient-count');
  const findRecipesBtn      = document.getElementById('find-recipes-btn');
  const recipeCardsContainer = document.getElementById('recipe-cards-container');
  const resultsSummary      = document.getElementById('results-summary');
  const detailContent       = document.getElementById('recipe-detail-content');
  const loadingOverlay      = document.getElementById('loading-overlay');
  const toastContainer      = document.getElementById('toast-container');
  
  // Navigation & Auth Elements
  const navLoginBtn         = document.getElementById('nav-login-btn');
  const navUserMenu         = document.getElementById('nav-user-menu');
  const navDashboardBtn     = document.getElementById('nav-dashboard-btn');
  const navLogoutBtn        = document.getElementById('nav-logout-btn');
  
  // Dashboard Elements
  const dashboardScreen     = document.getElementById('dashboard-screen');
  const wishlistContainer   = document.getElementById('wishlist-cards-container');

  // Auth State
  let currentUser = null;

  // ─── 1. Initialize ─────────────────────────────────────
  const init = async () => {
    try {
      // Fetch Ingredients & User State in parallel
      const [ingRes, userRes] = await Promise.all([
        fetch('/api/ingredients'),
        fetch('/api/user')
      ]);
      const ingData = await ingRes.json();
      allIngredients = ingData.ingredients || [];
      
      const userData = await userRes.json();
      if (userData.is_authenticated) {
        currentUser = userData;
        navLoginBtn.classList.add('hidden');
        navUserMenu.classList.remove('hidden');
      } else {
        navLoginBtn.classList.remove('hidden');
        navUserMenu.classList.add('hidden');
      }
    } catch (err) {
      console.error('Failed to initialize:', err);
    }
    setupListeners();
    updateButtonState();
  };

  init();

  // ─── Event Listeners ───────────────────────────────────
  const setupListeners = () => {
    ingredientInput.addEventListener('input', onInputChange);
    ingredientInput.addEventListener('keydown', onInputKeydown);

    document.addEventListener('click', (e) => {
      if (!ingredientInput.contains(e.target) && !autocompleteDropdown.contains(e.target)) {
        closeDropdown();
      }
    });

    findRecipesBtn.addEventListener('click', onFindRecipes);

    document.getElementById('back-to-input')
      ?.addEventListener('click', () => showScreen('input-screen'));
    document.getElementById('back-to-results')
      ?.addEventListener('click', () => {
        if (activeRecipe && activeRecipe.is_from_wishlist) {
            showScreen('dashboard-screen');
        } else {
            showScreen('results-screen');
        }
      });
      
    document.getElementById('back-to-input-from-dashboard')
      ?.addEventListener('click', () => showScreen('input-screen'));

    // Auth & Nav Listeners
    navLoginBtn?.addEventListener('click', () => window.location.href = '/login');
    navLogoutBtn?.addEventListener('click', () => window.location.href = '/logout');
    navDashboardBtn?.addEventListener('click', loadDashboard);
  };

  // ─── Wishlist Dashboard ────────────────────────────────
  const loadDashboard = async () => {
    showScreen('dashboard-screen');
    wishlistContainer.innerHTML = '<div style="text-align:center;width:100%;padding:40px;">Loading your wishlist...</div>';
    
    try {
      const res = await fetch('/api/wishlist');
      const data = await res.json();
      const saved = data.saved_recipes || [];
      
      if (saved.length === 0) {
        wishlistContainer.innerHTML = `
          <div class="no-results">
            <div class="no-results-icon">❤️</div>
            <h3>Your Wishlist is Empty</h3>
            <p>Recipes you save will appear here.</p>
          </div>`;
        return;
      }
      
      wishlistContainer.innerHTML = '';
      saved.forEach((recipe, i) => {
        recipe.is_from_wishlist = true; // flag to route back correctly
        const card = createRecipeCardElement(recipe, i);
        card.addEventListener('click', () => showRecipeDetail(recipe));
        wishlistContainer.appendChild(card);
      });
    } catch (err) {
      showToast('Failed to load wishlist.', 'error');
    }
  };

  // ─── 2. Autocomplete ───────────────────────────────────
  const onInputChange = () => {
    const query = ingredientInput.value.trim().toLowerCase();
    if (!query) { closeDropdown(); return; }

    const matches = allIngredients
      .filter(name => {
        const lower = name.toLowerCase();
        return lower.includes(query) &&
               !selectedIngredients.some(s => s.toLowerCase() === lower);
      })
      .slice(0, 8);

    if (!matches.length) { closeDropdown(); return; }
    renderDropdown(matches);
  };

  const renderDropdown = (matches) => {
    highlightIndex = -1;
    autocompleteDropdown.innerHTML = matches
      .map((name, i) => `<div class="autocomplete-item" data-index="${i}" data-value="${name}">${highlightMatch(name, ingredientInput.value.trim())}</div>`)
      .join('');

    autocompleteDropdown.querySelectorAll('.autocomplete-item').forEach(item => {
      item.addEventListener('click', () => selectIngredient(item.dataset.value));
    });

    autocompleteDropdown.classList.remove('hidden');
  };

  const highlightMatch = (name, query) => {
    const idx = name.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return name;
    return name.slice(0, idx) +
           `<span class="match-highlight">${name.slice(idx, idx + query.length)}</span>` +
           name.slice(idx + query.length);
  };

  const closeDropdown = () => {
    autocompleteDropdown.classList.add('hidden');
    autocompleteDropdown.innerHTML = '';
    highlightIndex = -1;
  };

  const onInputKeydown = (e) => {
    const items = autocompleteDropdown.querySelectorAll('.autocomplete-item');
    const isOpen = !autocompleteDropdown.classList.contains('hidden') && items.length > 0;

    switch (e.key) {
      case 'ArrowDown':
        if (!isOpen) return;
        e.preventDefault();
        highlightIndex = Math.min(highlightIndex + 1, items.length - 1);
        updateHighlight(items);
        break;
      case 'ArrowUp':
        if (!isOpen) return;
        e.preventDefault();
        highlightIndex = Math.max(highlightIndex - 1, 0);
        updateHighlight(items);
        break;
      case 'Enter':
        e.preventDefault();
        if (isOpen && highlightIndex >= 0 && highlightIndex < items.length) {
          selectIngredient(items[highlightIndex].dataset.value);
        }
        break;
      case 'Escape':
        closeDropdown();
        break;
    }
  };

  const updateHighlight = (items) => {
    items.forEach((item, i) => item.classList.toggle('active', i === highlightIndex));
    if (highlightIndex >= 0 && items[highlightIndex]) {
      items[highlightIndex].scrollIntoView({ block: 'nearest' });
    }
  };

  // ─── 3. Tag Management ─────────────────────────────────
  const selectIngredient = (name) => {
    const normalized = name.trim();
    if (!normalized) return;

    if (selectedIngredients.some(s => s.toLowerCase() === normalized.toLowerCase())) {
      showToast(`"${normalized}" is already added`, 'info');
      closeDropdown();
      ingredientInput.value = '';
      return;
    }

    selectedIngredients.push(normalized);
    renderTag(normalized);
    closeDropdown();
    ingredientInput.value = '';
    ingredientInput.focus();
    updateButtonState();
  };

  const renderTag = (name) => {
    const tag = document.createElement('div');
    tag.className = 'ingredient-tag';
    tag.dataset.ingredient = name.toLowerCase();
    tag.innerHTML = `
      <span>${name}</span>
      <button class="tag-remove" aria-label="Remove ${name}">&times;</button>
    `;
    tag.querySelector('.tag-remove').addEventListener('click', () => removeTag(tag, name));
    ingredientTags.appendChild(tag);
  };

  const removeTag = (tagEl, name) => {
    tagEl.classList.add('tag-exit');
    setTimeout(() => {
      tagEl.remove();
      selectedIngredients = selectedIngredients.filter(
        s => s.toLowerCase() !== name.toLowerCase()
      );
      updateButtonState();
    }, 300);
  };

  // ─── 4. Find Recipes ───────────────────────────────────
  const updateButtonState = () => {
    const count = selectedIngredients.length;
    ingredientCount.textContent = `${count} ingredient${count !== 1 ? 's' : ''} selected`;

    if (count < 2) {
      findRecipesBtn.classList.add('disabled');
      findRecipesBtn.disabled = true;
    } else {
      findRecipesBtn.classList.remove('disabled');
      findRecipesBtn.disabled = false;
    }
  };

  const onFindRecipes = async () => {
    if (selectedIngredients.length < 2) {
      showToast('Please select at least 2 ingredients.', 'error');
      return;
    }

    // Loading state
    findRecipesBtn.classList.add('loading');
    const btnText = findRecipesBtn.querySelector('.btn-text');
    const originalText = btnText.textContent;
    btnText.textContent = 'Searching...';
    findRecipesBtn.disabled = true;
    loadingOverlay.classList.remove('hidden');

    try {
      const res = await fetch('/api/find-recipes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ingredients: selectedIngredients }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `Server error ${res.status}`);
      }

      const data = await res.json();

      if (data.error) {
        showToast(data.error, 'error');
        return;
      }

      currentResults = data.recipes || [];

      if (currentResults.length === 0) {
        showToast('No matching recipes found. Try different ingredients.', 'info');
      }

      renderRecipeCards(currentResults);
      resultsSummary.textContent = `Found ${currentResults.length} recipe${currentResults.length !== 1 ? 's' : ''} matching your ingredients`;
      showScreen('results-screen');

    } catch (err) {
      console.error('Recipe search error:', err);
      showToast(err.message || 'Something went wrong. Please try again.', 'error');
    } finally {
      findRecipesBtn.classList.remove('loading');
      btnText.textContent = originalText;
      updateButtonState();
      loadingOverlay.classList.add('hidden');
    }
  };

  // ─── 5. Recipe Cards ───────────────────────────────────
  const renderRecipeCards = (recipes) => {
    recipeCardsContainer.innerHTML = '';

    if (!recipes.length) {
      recipeCardsContainer.innerHTML = `
        <div class="no-results">
          <div class="no-results-icon">🍽️</div>
          <h3>No Recipes Found</h3>
          <p>Try adding different or more ingredients to find matching recipes.</p>
        </div>`;
      return;
    }

    // SVG gradient definition (shared)
    const svgDefs = `
      <svg width="0" height="0" style="position:absolute">
        <defs>
          <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#f59e0b"/>
            <stop offset="100%" stop-color="#f97316"/>
          </linearGradient>
        </defs>
      </svg>`;
    recipeCardsContainer.insertAdjacentHTML('afterbegin', svgDefs);

    recipes.forEach((recipe, index) => {
      const card = createRecipeCardElement(recipe, index);
      card.addEventListener('click', () => showRecipeDetail(recipe));
      recipeCardsContainer.appendChild(card);
    });
  };

  const createRecipeCardElement = (recipe, index) => {
      const score = recipe.match_score || 0;
      const name = recipe.name || 'Untitled Recipe';
      const cuisine = recipe.cuisine_type || 'General';
      const totalTime = recipe.total_time_minutes || recipe.cooking_time_minutes || 0;
      const difficulty = recipe.difficulty_level || 'Medium';
      const servings = recipe.servings || '—';
      const description = recipe.description || '';

      // SVG ring math
      const radius = 28;
      const circumference = 2 * Math.PI * radius;
      const dashOffset = circumference * (1 - score / 100);

      const card = document.createElement('div');
      card.className = 'recipe-card';
      card.style.animationDelay = `${index * 100}ms`;

      card.innerHTML = `
        <div class="card-top-row">
          <div class="card-info">
            <h3>${name}</h3>
            <span class="cuisine-badge">${cuisine}</span>
          </div>
          <div class="score-ring-container">
            <svg class="score-ring-svg" viewBox="0 0 68 68">
              <circle class="score-ring-bg" cx="34" cy="34" r="${radius}"/>
              <circle class="score-ring-fill" cx="34" cy="34" r="${radius}"
                      stroke="url(#scoreGradient)"
                      stroke-dasharray="${circumference}"
                      stroke-dashoffset="${dashOffset}"/>
            </svg>
            <div class="score-ring-text">
              <span class="score-value">${Math.round(score)}</span>
              <span class="score-label">match</span>
            </div>
          </div>
        </div>
        <p class="card-description">${description}</p>
        <div class="card-meta">
          <span class="card-meta-item"><span class="meta-icon">🕐</span> ${formatTime(totalTime)}</span>
          <span class="card-meta-item"><span class="meta-icon">📊</span> ${difficulty}</span>
          <span class="card-meta-item"><span class="meta-icon">🍽️</span> ${servings} servings</span>
        </div>
      `;
      return card;
  };

  // ─── 6. Recipe Detail ──────────────────────────────────
  let activeRecipe = null;
  let baseServings = 1;
  let currentServings = 1;

  const showRecipeDetail = (recipe) => {
    activeRecipe = recipe;
    baseServings = parseInt(recipe.servings) || 2;
    currentServings = baseServings;

    const name = recipe.name || 'Untitled Recipe';
    const cuisine = recipe.cuisine_type || 'General';
    const prepTime = recipe.prep_time_minutes;
    const cookTime = recipe.cooking_time_minutes;
    const totalTime = recipe.total_time_minutes;
    const difficulty = recipe.difficulty_level || 'Medium';
    const score = recipe.match_score || 0;
    const steps = recipe.steps || [];

    // Step completion from localStorage
    const storageKey = `recipe-steps-${name}`;
    const completedSteps = loadCompletedSteps(storageKey);

    // SVG ring
    const radius = 28;
    const circumference = 2 * Math.PI * radius;
    const dashOffset = circumference * (1 - score / 100);

    detailContent.innerHTML = `
      <!-- Summary Panel -->
      <div class="detail-summary">
        ${currentUser && !recipe.is_from_wishlist ? `<button id="btn-save-wishlist" class="btn-wishlist">❤️ Save to Wishlist</button>` : ''}
        ${recipe.is_from_wishlist ? `<div style="position:absolute;top:24px;right:24px;color:#ef4444;font-size:0.875rem;font-weight:600;">❤️ Saved</div>` : ''}
        
        <div class="detail-title">${name}</div>
        <div class="detail-cuisine">
          <span class="cuisine-badge">${cuisine}</span>
        </div>
        <div class="detail-meta-grid">
          ${prepTime ? `<div class="detail-meta-card"><div class="meta-value">${formatTime(prepTime)}</div><div class="meta-label">Prep Time</div></div>` : ''}
          ${cookTime ? `<div class="detail-meta-card"><div class="meta-value">${formatTime(cookTime)}</div><div class="meta-label">Cook Time</div></div>` : ''}
          ${totalTime ? `<div class="detail-meta-card"><div class="meta-value">${formatTime(totalTime)}</div><div class="meta-label">Total Time</div></div>` : ''}
          <div class="detail-meta-card"><div class="meta-value">${difficulty}</div><div class="meta-label">Difficulty</div></div>
          
          <div class="detail-meta-card servings-card">
            <div class="servings-controls">
              <button class="serving-btn" id="btn-dec-servings">-</button>
              <div class="meta-value" id="current-servings-display">${currentServings}</div>
              <button class="serving-btn" id="btn-inc-servings">+</button>
            </div>
            <div class="meta-label">Servings</div>
          </div>

          <div class="detail-meta-card">
            <div class="meta-value" style="display:flex;align-items:center;justify-content:center">
              <svg width="48" height="48" viewBox="0 0 68 68">
                <circle class="score-ring-bg" cx="34" cy="34" r="${radius}"/>
                <circle class="score-ring-fill" cx="34" cy="34" r="${radius}"
                        stroke="url(#scoreGradient)"
                        stroke-dasharray="${circumference}"
                        stroke-dashoffset="${dashOffset}"/>
              </svg>
            </div>
            <div class="meta-label">${Math.round(score)}% Match</div>
          </div>
        </div>
      </div>

      <!-- Dynamic Ingredients Container -->
      <div id="dynamic-ingredients-container"></div>

      <!-- Preparation Steps -->
      ${steps.length > 0 ? `
        <div class="detail-section">
          <h3 class="detail-section-title">👨‍🍳 Preparation Steps</h3>
          <div class="steps-list">
            ${steps.map((step, idx) => {
              const done = completedSteps.includes(idx);
              return `
                <div class="step-item ${done ? 'completed' : ''}" data-step="${idx}">
                  <div class="step-number"><span>${idx + 1}</span></div>
                  <div class="step-text">${step}</div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      ` : ''}
    `;

    // SVG gradient (needed in detail view)
    if (!document.getElementById('scoreGradientDef')) {
      const svgDefs = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svgDefs.id = 'scoreGradientDef';
      svgDefs.setAttribute('width', '0');
      svgDefs.setAttribute('height', '0');
      svgDefs.style.position = 'absolute';
      svgDefs.innerHTML = `<defs><linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#f59e0b"/><stop offset="100%" stop-color="#f97316"/>
      </linearGradient></defs>`;
      document.body.appendChild(svgDefs);
    }

    // Wire step completion toggles
    detailContent.querySelectorAll('.step-item').forEach(item => {
      item.addEventListener('click', () => {
        const stepIdx = parseInt(item.dataset.step, 10);
        item.classList.toggle('completed');
        toggleStepCompletion(storageKey, stepIdx);
      });
    });

    // Wire servings controls
    document.getElementById('btn-dec-servings').addEventListener('click', () => {
      if (currentServings > 1) {
        currentServings--;
        document.getElementById('current-servings-display').textContent = currentServings;
        renderDynamicIngredients();
      }
    });
    
    document.getElementById('btn-inc-servings').addEventListener('click', () => {
      if (currentServings < 20) {
        currentServings++;
        document.getElementById('current-servings-display').textContent = currentServings;
        renderDynamicIngredients();
      }
    });

    // Wire Wishlist Save button
    const saveBtn = document.getElementById('btn-save-wishlist');
    if (saveBtn) {
      saveBtn.addEventListener('click', async () => {
        saveBtn.disabled = true;
        saveBtn.innerHTML = 'Saving...';
        try {
          const res = await fetch('/api/wishlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipe: activeRecipe })
          });
          const data = await res.json();
          if (res.ok) {
            saveBtn.classList.add('saved');
            saveBtn.innerHTML = '❤️ Saved';
            showToast('Recipe saved to your wishlist!', 'success');
          } else {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '❤️ Save to Wishlist';
            showToast(data.message || data.error, 'error');
          }
        } catch (e) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = '❤️ Save to Wishlist';
          showToast('Network error while saving.', 'error');
        }
      });
    }

    renderDynamicIngredients();
    showScreen('detail-screen');
  };

  const renderDynamicIngredients = () => {
    if (!activeRecipe) return;
    
    const container = document.getElementById('dynamic-ingredients-container');
    const multiplier = currentServings / baseServings;
    const ingredients = activeRecipe.ingredients || [];
    const substitutions = activeRecipe.substitutions || {};

    const available = ingredients.filter(i => i.is_available && !i.is_optional);
    const missing = ingredients.filter(i => !i.is_available && !i.is_optional);
    const optional = ingredients.filter(i => i.is_optional && !i.is_available);

    const formatQuantity = (ing) => {
      if (ing.amount == null) return ing.original_string || '';
      // Scale amount and format cleanly (e.g. 1.5 instead of 1.5000000)
      const scaled = (ing.amount * multiplier);
      // Show up to 1 decimal place, strip trailing zeroes
      const formattedNum = Number.isInteger(scaled) ? scaled : scaled.toFixed(1).replace(/\.0$/, '');
      const unitStr = ing.unit ? ` ${ing.unit}` : '';
      return `${formattedNum}${unitStr}`;
    };

    container.innerHTML = `
      <!-- Available Ingredients -->
      ${available.length > 0 ? `
        <div class="detail-section">
          <h3 class="detail-section-title">✅ Available Ingredients</h3>
          <div class="ingredients-list">
            ${available.map(ing => `
              <div class="ingredient-item available">
                <span class="ingredient-status-icon">✓</span>
                <span class="ingredient-name">${ing.name}</span>
                <span class="ingredient-quantity scaled-quantity">${formatQuantity(ing)}</span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <!-- Missing Ingredients -->
      ${missing.length > 0 ? `
        <div class="detail-section">
          <h3 class="detail-section-title">❌ Missing Ingredients</h3>
          <div class="ingredients-list">
            ${missing.map(ing => `
              <div class="ingredient-item missing">
                <span class="ingredient-status-icon">✗</span>
                <span class="ingredient-name">${ing.name}</span>
                <span class="ingredient-quantity scaled-quantity">${formatQuantity(ing)}</span>
              </div>
              ${renderSubstitutions(substitutions[ing.name])}
            `).join('')}
          </div>
        </div>
      ` : ''}

      <!-- Optional Missing -->
      ${optional.length > 0 ? `
        <div class="detail-section">
          <h3 class="detail-section-title">🔸 Optional (Missing)</h3>
          <div class="ingredients-list">
            ${optional.map(ing => `
              <div class="ingredient-item optional">
                <span class="ingredient-status-icon">~</span>
                <span class="ingredient-name">${ing.name}</span>
                <span class="ingredient-quantity scaled-quantity">${formatQuantity(ing)}</span>
              </div>
              ${renderSubstitutions(substitutions[ing.name])}
            `).join('')}
          </div>
        </div>
      ` : ''}
    `;
  };

  // ─── Substitution Rendering ─────────────────────────────
  const renderSubstitutions = (subs) => {
    if (!subs || !subs.length) return '';

    return `
      <div class="substitution-panel">
        <div class="substitution-title">Suggested Substitutes</div>
        ${subs.slice(0, 3).map(sub => `
          <div class="substitute-item">
            <span class="substitute-name">${sub.name || sub}</span>
            ${sub.suitability_score ? `
              <div class="substitute-score-bar">
                <div class="substitute-score-fill" style="width: ${sub.suitability_score * 10}%"></div>
              </div>
              <span class="substitute-score-value">${sub.suitability_score}/10</span>
            ` : ''}
            ${sub.adjustment_note ? `<span class="substitute-note">${sub.adjustment_note}</span>` : ''}
          </div>
        `).join('')}
      </div>
    `;
  };

  // ─── Step Completion Persistence ────────────────────────
  const loadCompletedSteps = (key) => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : [];
    } catch { return []; }
  };

  const toggleStepCompletion = (key, stepIdx) => {
    const completed = loadCompletedSteps(key);
    const pos = completed.indexOf(stepIdx);
    if (pos === -1) completed.push(stepIdx);
    else completed.splice(pos, 1);
    try { localStorage.setItem(key, JSON.stringify(completed)); }
    catch (e) { console.warn('Could not persist step:', e); }
  };

  // ─── 7. Screen Navigation ──────────────────────────────
  const showScreen = (screenId) => {
    [inputScreen, resultsScreen, detailScreen, dashboardScreen].forEach(s => {
      if (s) s.classList.remove('screen-active');
    });

    const target = document.getElementById(screenId);
    if (target) {
      requestAnimationFrame(() => {
        target.classList.add('screen-active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
  };

  // ─── 8. Toast Notifications ─────────────────────────────
  const showToast = (message, type = 'info') => {
    const icons = { success: '✓', error: '✗', info: 'ℹ' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ'}</span><span class="toast-message">${message}</span>`;

    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('toast-exit');
      setTimeout(() => toast.remove(), 400);
    }, 4000);
  };

  // ─── 10. Helpers ────────────────────────────────────────
  const formatTime = (minutes) => {
    const m = parseInt(minutes, 10);
    if (isNaN(m) || m <= 0) return `${minutes || '—'}`;
    const hrs = Math.floor(m / 60);
    const mins = m % 60;
    if (hrs > 0 && mins > 0) return `${hrs}h ${mins}m`;
    if (hrs > 0) return `${hrs}h`;
    return `${mins}m`;
  };

});
