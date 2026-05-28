// ===== CONFIG =====
const API_URL = 'http://localhost:5000';

// ===== STATE =====
let currentUser = null;
let currentToken = null;
let places = [];
let currentFeedbackPlaceId = null;
let currentFilter = 'all';
const visitedOverrides = new Map();
const visitedRequestTokens = new Map();
let visitedRequestCounter = 0;

// ===== INIT =====
document.addEventListener('DOMContentLoaded', init);

function init() {
  bindEvents();
  applyStoredTheme();
  restoreSession();
  switchTab('login');
}

function bindEvents() {
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const addPlaceForm = document.getElementById('addPlaceForm');
  const feedbackForm = document.getElementById('feedbackForm');
  const themeToggle = document.getElementById('themeToggle');

  if (loginForm) loginForm.addEventListener('submit', handleLogin);
  if (registerForm) registerForm.addEventListener('submit', handleRegister);
  if (addPlaceForm) addPlaceForm.addEventListener('submit', handleAddPlace);
  if (feedbackForm) feedbackForm.addEventListener('submit', handleAddFeedback);
  if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
}

function restoreSession() {
  const token = localStorage.getItem('token');
  const user = localStorage.getItem('user');

  if (!token || !user) {
    showAuthPage();
    return;
  }

  try {
    currentToken = token;
    currentUser = JSON.parse(user);
    showPlacesPage();
    loadPlaces();
  } catch (error) {
    logout();
  }
}

// ===== NAVIGATION =====
function showAuthPage() {
  document.getElementById('authPage')?.classList.add('active');
  document.getElementById('placesPage')?.classList.remove('active');
}

function showPlacesPage() {
  document.getElementById('authPage')?.classList.remove('active');
  document.getElementById('placesPage')?.classList.add('active');
  syncUserHeader();
}

function switchTab(tab) {
  document.querySelectorAll('.auth-tab').forEach((button) => {
    button.classList.toggle('active', button.dataset.tab === tab);
  });

  document.querySelectorAll('.auth-form').forEach((form) => {
    form.classList.toggle('active', form.id === `${tab}Form`);
  });

  clearAllAuthErrors();
}

function syncUserHeader() {
  if (!currentUser) return;

  const username = String(currentUser.username || 'Usuário');
  const avatarText = username.trim().charAt(0).toUpperCase() || 'V';

  const userText = document.getElementById('navbarUserText');
  const avatar = document.getElementById('navbarAvatar');
  const dropdownUserName = document.getElementById('dropdownUserName');

  if (userText) userText.textContent = username;
  if (avatar) avatar.textContent = avatarText;
  if (dropdownUserName) dropdownUserName.textContent = username;
}

function toggleMobileDropdown() {
  const dropdown = document.getElementById('navbarDropdown');
  if (!dropdown) return;
  dropdown.classList.toggle('active');
  
  if (dropdown.classList.contains('active')) {
    document.addEventListener('click', closeMobileDropdownOnClickOutside);
  } else {
    document.removeEventListener('click', closeMobileDropdownOnClickOutside);
  }
}

function closeMobileDropdownOnClickOutside(event) {
  const dropdown = document.getElementById('navbarDropdown');
  const avatar = document.getElementById('navbarAvatar');
  
  if (!dropdown || !avatar) return;
  if (dropdown.contains(event.target) || avatar.contains(event.target)) return;
  
  dropdown.classList.remove('active');
  document.removeEventListener('click', closeMobileDropdownOnClickOutside);
}

// ===== AUTH =====
async function handleLogin(event) {
  event.preventDefault();
  clearAllAuthErrors();

  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;

  if (!email) {
    showFieldError('loginEmailError', 'Informe o email.');
    return;
  }

  if (!password) {
    showFieldError('loginPasswordError', 'Informe a senha.');
    return;
  }

  try {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await safeJson(response);

    if (!response.ok) {
      showError('loginFormError', data.message || 'Erro ao fazer login.');
      return;
    }

    currentToken = data.token;
    currentUser = data.user;
    localStorage.setItem('token', currentToken);
    localStorage.setItem('user', JSON.stringify(currentUser));

    document.getElementById('loginForm').reset();
    showPlacesPage();
    await loadPlaces();
  } catch (error) {
    showError('loginFormError', 'Erro de conexão com a API.');
  }
}

async function handleRegister(event) {
  event.preventDefault();
  clearAllAuthErrors();

  const username = document.getElementById('registerUsername').value.trim();
  const email = document.getElementById('registerEmail').value.trim();
  const password = document.getElementById('registerPassword').value;

  if (!username) {
    showFieldError('registerUsernameError', 'Informe o nome de usuário.');
    return;
  }

  if (!email) {
    showFieldError('registerEmailError', 'Informe o email.');
    return;
  }

  if (!password) {
    showFieldError('registerPasswordError', 'Informe a senha.');
    return;
  }

  try {
    const response = await fetch(`${API_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });

    const data = await safeJson(response);

    if (!response.ok) {
      showError('registerFormError', data.message || 'Erro ao cadastrar.');
      return;
    }

    currentToken = data.token;
    currentUser = data.user;
    localStorage.setItem('token', currentToken);
    localStorage.setItem('user', JSON.stringify(currentUser));

    document.getElementById('registerForm').reset();
    showPlacesPage();
    await loadPlaces();
  } catch (error) {
    showError('registerFormError', 'Erro de conexão com a API.');
  }
}

function logout() {
  currentUser = null;
  currentToken = null;
  places = [];
  currentFeedbackPlaceId = null;

  localStorage.removeItem('token');
  localStorage.removeItem('user');

  document.getElementById('loginForm')?.reset();
  document.getElementById('registerForm')?.reset();
  hideModal('addPlaceModal');
  hideModal('feedbackModal');
  clearAllAuthErrors();
  showAuthPage();
  switchTab('login');
}

// ===== PLACES =====
async function loadPlaces() {
  if (!currentToken) return;

  try {
    const response = await fetch(`${API_URL}/places`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });

    if (!response.ok) {
      if (response.status === 401) {
        logout();
      }
      return;
    }

    places = await safeJson(response);
    renderPlaces();
  } catch (error) {
    showPlacesEmptyFallback();
  }
}

async function handleAddPlace(event) {
  event.preventDefault();
  clearFormErrors(['addPlaceNameError', 'addPlaceMapsError', 'addPlacePhotoError', 'addPlaceFormError']);

  const name = document.getElementById('placeName').value.trim();
  const mapsUrl = document.getElementById('placeMapsUrl').value.trim();
  const photoUrl = (document.getElementById('placePhotoUrl') && document.getElementById('placePhotoUrl').value) ? document.getElementById('placePhotoUrl').value.trim() : '';

  if (!name) {
    showFieldError('addPlaceNameError', 'Informe o nome do lugar.');
    return;
  }

  if (!mapsUrl) {
    showFieldError('addPlaceMapsError', 'Informe o link do Maps.');
    return;
  }

  if (!Array.isArray(places)) {
    places = [];
  }

  const tempId = `temp-${Date.now()}`;
  const optimisticPlace = {
    id: tempId,
    user_id: currentUser?.id,
    name,
    maps_url: mapsUrl,
    photo_url: photoUrl,
    visited: false,
    feedback: ''
  };

  places = [optimisticPlace, ...places];
  renderPlaces();

  document.getElementById('addPlaceForm').reset();
  closeModal('addPlaceModal');

  try {
    const response = await fetch(`${API_URL}/places`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${currentToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name, maps_url: mapsUrl, photo_url: photoUrl })
    });

    const data = await safeJson(response);

    if (!response.ok) {
      places = places.filter((place) => place.id !== tempId);
      renderPlaces();
      showToast(data.message || 'Erro ao adicionar lugar.', 'error');
      return;
    }

    places = places.map((place) => (place.id === tempId ? data : place));
    renderPlaces();
    showToast('Lugar adicionado com sucesso!', 'success');
  } catch (error) {
    places = places.filter((place) => place.id !== tempId);
    renderPlaces();
    showToast('Erro ao adicionar lugar.', 'error');
  }
}

async function markAsVisited(placeId, button) {
  const place = getPlaceById(placeId);
  if (!place) return;

  const previousVisited = normalizeVisited(place.visited);
  const nextVisited = !previousVisited;

  visitedOverrides.set(String(placeId), nextVisited);
  place.visited = nextVisited;
  updatePlaceCardUI(button, nextVisited);

  const requestId = (visitedRequestCounter += 1);
  visitedRequestTokens.set(String(placeId), requestId);

  try {
    const response = await fetch(`${API_URL}/places/${encodeURIComponent(placeId)}`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${currentToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ visited: nextVisited })
    });

    if (!response.ok) {
      const data = await safeJson(response);
      showToast(data.message || 'Erro ao marcar como visitado.', 'error');
      if (visitedRequestTokens.get(String(placeId)) !== requestId) return;
      visitedOverrides.delete(String(placeId));
      place.visited = previousVisited;
      updatePlaceCardUI(button, previousVisited);
      return;
    }
    if (visitedRequestTokens.get(String(placeId)) !== requestId) return;
    visitedOverrides.delete(String(placeId));
    showToast(nextVisited ? 'Marcado como visitado!' : 'Removido da lista de visitados.', 'success');
  } catch (error) {
    showToast('Erro ao marcar como visitado.', 'error');
    if (visitedRequestTokens.get(String(placeId)) !== requestId) return;
    visitedOverrides.delete(String(placeId));
    place.visited = previousVisited;
    updatePlaceCardUI(button, previousVisited);
  }
}

function updatePlaceCardUI(button, isVisited) {
  if (!button) return;
  const card = button.closest('.place-card');
  if (!card) return;

  const badge = card.querySelector('.place-card__badge');
  const feedbackButton = card.querySelector('.action-button--feedback');

  if (badge) {
    badge.textContent = isVisited ? '✅ Visitado' : '📍 Na lista';
    badge.classList.toggle('place-card__badge--visited', isVisited);
    badge.classList.toggle('place-card__badge--pending', !isVisited);
  }

  button.textContent = isVisited ? 'Visitado ✓' : '✓ Visitei';
  button.classList.toggle('is-visited', isVisited);

  if (feedbackButton) {
    if (isVisited) {
      feedbackButton.removeAttribute('disabled');
      feedbackButton.removeAttribute('aria-disabled');
    } else {
      feedbackButton.setAttribute('disabled', '');
      feedbackButton.setAttribute('aria-disabled', 'true');
    }
  }
}

async function deletePlace(placeId, button) {
  if (!confirm('Deletar este lugar?')) return;

  const previousPlaces = places.slice();
  places = places.filter((place) => String(place.id) !== String(placeId));
  renderPlaces();

  const card = button?.closest?.('.place-card');
  if (card) card.remove();

  try {
    const response = await fetch(`${API_URL}/places/${encodeURIComponent(placeId)}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${currentToken}` }
    });

    if (!response.ok) {
      const data = await safeJson(response);
      showToast(data.message || 'Erro ao deletar lugar.', 'error');
      places = previousPlaces;
      renderPlaces();
    } else {
      showToast('Lugar deletado com sucesso!', 'success');
    }
  } catch (error) {
    showToast('Erro ao deletar lugar.', 'error');
    places = previousPlaces;
    renderPlaces();
  }
}

// ===== FEEDBACK =====
function openFeedbackModal(placeId) {
  currentFeedbackPlaceId = placeId;
  clearFormErrors(['feedbackTextError', 'feedbackFormError']);

  const place = getPlaceById(placeId);
  const feedbackInput = document.getElementById('feedbackText');
  if (feedbackInput) {
    feedbackInput.value = place?.feedback ? String(place.feedback) : '';
  }

  openModal('feedbackModal');
}

async function handleAddFeedback(event) {
  event.preventDefault();
  clearFormErrors(['feedbackTextError', 'feedbackFormError']);

  const feedback = document.getElementById('feedbackText').value.trim();

  if (!currentFeedbackPlaceId) {
    showError('feedbackFormError', 'Selecione um lugar primeiro.');
    return;
  }

  if (!feedback) {
    showFieldError('feedbackTextError', 'Escreva um feedback.');
    return;
  }

  try {
    const response = await fetch(`${API_URL}/places/${encodeURIComponent(currentFeedbackPlaceId)}/feedback`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${currentToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ feedback })
    });

    const data = await safeJson(response);

    if (!response.ok) {
      showError('feedbackFormError', data.message || 'Erro ao salvar feedback.');
      return;
    }

    document.getElementById('feedbackForm').reset();
    closeModal('feedbackModal');
    await loadPlaces();
    showToast('Feedback adicionado com sucesso!', 'success');
  } catch (error) {
    showError('feedbackFormError', 'Erro ao salvar feedback.');
  }
}

// ===== RENDERING =====
function setFilter(filter) {
  currentFilter = filter;
  
  // Update button active states
  document.querySelectorAll('.filter-btn').forEach((btn) => {
    btn.classList.toggle('filter-btn--active', btn.dataset.filter === filter);
  });
  
  renderPlaces();
}

function renderPlaces() {
  const grid = document.getElementById('placesGrid');
  const emptyState = document.getElementById('emptyState');

  if (!grid) return;

  if (!places.length) {
    grid.innerHTML = '';
    if (emptyState) {
      grid.appendChild(emptyState);
      emptyState.style.display = 'grid';
    }
    return;
  }

  if (emptyState) {
    emptyState.style.display = 'none';
  }

  // Separate and sort places
  const pending = places
    .filter(p => !normalizeVisited(p.visited))
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  
  const visited = places
    .filter(p => normalizeVisited(p.visited))
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));

  // Filter based on current filter
  let sectionsToShow = [];
  
  if (currentFilter === 'all') {
    if (pending.length > 0) sectionsToShow.push({ title: '📍 Para visitar', count: pending.length, places: pending });
    if (visited.length > 0) sectionsToShow.push({ title: '✅ Já visitamos', count: visited.length, places: visited });
  } else if (currentFilter === 'pending') {
    if (pending.length > 0) sectionsToShow.push({ title: '📍 Para visitar', count: pending.length, places: pending });
  } else if (currentFilter === 'visited') {
    if (visited.length > 0) sectionsToShow.push({ title: '✅ Já visitamos', count: visited.length, places: visited });
  }

  if (!sectionsToShow.length) {
    grid.innerHTML = '';
    if (emptyState) {
      grid.appendChild(emptyState);
      emptyState.style.display = 'grid';
    }
    return;
  }

  grid.innerHTML = sectionsToShow
    .map(section => {
      const cardsHtml = section.places
        .map(place => renderPlaceCard(place))
        .join('');
      
      return `
        <div class="places-section">
          <header class="places-section-header">${section.title} (${section.count})</header>
          ${cardsHtml}
        </div>
      `;
    })
    .join('');
}

function renderPlaceCard(place) {
  const safeId = escapeJs(String(place.id ?? ''));
  const name = escapeHtml(place.name ?? 'Lugar sem nome');
  const mapsUrl = escapeAttr(place.maps_url ?? '#');
  const photoRaw = place.photo_url ?? '';
  const photoUrl = photoRaw ? escapeAttr(photoRaw) : '';
  const override = visitedOverrides.get(String(place.id ?? safeId));
  const isVisited = typeof override === 'boolean' ? override : normalizeVisited(place.visited);
  const badgeClass = isVisited ? 'place-card__badge--visited' : 'place-card__badge--pending';
  const badgeText = isVisited ? '✅ Visitado' : '📍 Na lista';
  const feedback = place.feedback ? `<p class="place-card__feedback">"${escapeHtml(place.feedback)}"</p>` : '';
  const color = hashColor(String(place.name ?? place.id ?? 'V'));
  const feedbackDisabledAttr = !isVisited ? 'disabled aria-disabled="true" title="Marque como visitado primeiro"' : 'title="Feedback"';
  const visitedLabel = isVisited ? 'Visitado ✓' : '✓ Visitei';
  const visitedClass = isVisited ? 'is-visited' : '';

  if (photoUrl) {
    return `
      <article class="place-card place-card--with-photo" data-id="${safeId}">
        <img class="place-card__photo" src="${photoUrl}" alt="${name}" onerror="this.style.display='none';this.closest('.place-card').classList.remove('place-card--with-photo')">
        <div class="place-card__row">
          <div class="place-card__emoji" aria-hidden="true" style="background:${color};">${String((place.name||'')[0]||'V').toUpperCase()}</div>
          <div class="place-card__body">
            <h3 class="place-card__name">${name}</h3>
            <div class="place-card__meta">
              <span class="place-card__badge ${badgeClass}">${badgeText}</span>
              <a class="place-card__maps" href="${mapsUrl}" target="_blank" rel="noopener noreferrer">Ver no Maps →</a>
            </div>
            ${feedback}
          </div>
          <div class="place-card__actions">
            <button type="button" class="action-button action-button--visited ${visitedClass}" onclick="markAsVisited('${safeId}', this)" title="Marcar visitado">${visitedLabel}</button>
            <button type="button" class="action-button action-button--feedback" ${feedbackDisabledAttr} onclick="openFeedbackModal('${safeId}')">💬</button>
            <button type="button" class="action-button action-button--delete" onclick="deletePlace('${safeId}', this)" title="Excluir lugar">🗑</button>
          </div>
        </div>
      </article>
    `;
  }

  return `
    <article class="place-card" data-id="${safeId}">
      <div class="place-card__emoji" aria-hidden="true" style="background:${color};">${String((place.name||'')[0]||'V').toUpperCase()}</div>
      <div class="place-card__body">
        <h3 class="place-card__name">${name}</h3>
        <div class="place-card__meta">
          <span class="place-card__badge ${badgeClass}">${badgeText}</span>
          <a class="place-card__maps" href="${mapsUrl}" target="_blank" rel="noopener noreferrer">Ver no Maps →</a>
        </div>
        ${feedback}
      </div>
      <div class="place-card__actions">
        <button type="button" class="action-button action-button--visited ${visitedClass}" onclick="markAsVisited('${safeId}', this)" title="Marcar visitado">${visitedLabel}</button>
        <button type="button" class="action-button action-button--feedback" ${feedbackDisabledAttr} onclick="openFeedbackModal('${safeId}')">💬</button>
        <button type="button" class="action-button action-button--delete" onclick="deletePlace('${safeId}', this)" title="Excluir lugar">🗑</button>
      </div>
    </article>
  `;
}

function showPlacesEmptyFallback() {
  const grid = document.getElementById('placesGrid');
  const emptyState = document.getElementById('emptyState');

  if (grid) grid.innerHTML = '';
  if (emptyState) {
    grid?.appendChild(emptyState);
    emptyState.style.display = 'grid';
  }
}

function hashColor(input) {
  const hash = hashString(input);
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue} 65% 45%)`;
}

// ===== THEME =====
function applyStoredTheme() {
  const storedTheme = localStorage.getItem('theme');
  const theme = storedTheme === 'dark' ? 'dark' : 'light';
  applyTheme(theme);
}

function applyTheme(theme) {
  const isDark = theme === 'dark';
  document.body.classList.toggle('dark-mode', isDark);
  localStorage.setItem('theme', theme);

  const toggle = document.getElementById('themeToggle');
  if (toggle) {
    toggle.setAttribute('aria-label', isDark ? 'Ativar modo claro' : 'Ativar modo escuro');
  }
}

function toggleTheme() {
  const isDark = document.body.classList.contains('dark-mode');
  applyTheme(isDark ? 'light' : 'dark');
}

// ===== TOAST =====
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  const toastCount = container.querySelectorAll('.toast:not(.exiting)').length;
  if (toastCount > 3) {
    const oldestToast = container.querySelector('.toast:not(.exiting)');
    if (oldestToast) {
      oldestToast.classList.add('exiting');
      setTimeout(() => oldestToast.remove(), 300);
    }
  }

  setTimeout(() => {
    toast.classList.add('exiting');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ===== MODALS =====
function openAddPlaceModal() {
  clearFormErrors(['addPlaceNameError', 'addPlaceMapsError', 'addPlaceFormError']);
  document.getElementById('addPlaceForm')?.reset();
  openModal('addPlaceModal');
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;

  modal.classList.add('is-open');
  document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;

  modal.classList.remove('is-open');
  if (modalId === 'feedbackModal') {
    currentFeedbackPlaceId = null;
  }

  document.body.style.overflow = '';
}

function hideModal(modalId) {
  document.getElementById(modalId)?.classList.remove('is-open');
  document.body.style.overflow = '';
}

// ===== HELPERS =====
function getPlaceById(placeId) {
  return places.find((place) => String(place.id) === String(placeId));
}

function normalizeVisited(value) {
  if (value === true || value === 1 || value === '1') return true;
  if (typeof value === 'string') {
    return value.trim().toLowerCase() === 'true';
  }
  return false;
}

function getPlaceGradient(input) {
  const hash = hashString(input);
  const hue = Math.abs(hash) % 360;
  const hue2 = (hue + 40) % 360;
  return `linear-gradient(135deg, hsl(${hue} 65% 55%), hsl(${hue2} 70% 60%))`;
}

function hashString(value) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = ((hash << 5) - hash) + value.charCodeAt(index);
    hash |= 0;
  }
  return hash;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeAttr(value) {
  return escapeHtml(value);
}

function escapeJs(value) {
  return String(value)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/\r/g, '')
    .replace(/\n/g, '');
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch (error) {
    return {};
  }
}

function showError(elementId, message) {
  const element = document.getElementById(elementId);
  if (!element) return;

  const text = element.querySelector('.form-error__text');
  if (text) {
    text.textContent = message;
  } else {
    element.textContent = message;
  }

  element.classList.add('is-visible');
}

function showFieldError(elementId, message) {
  const element = document.getElementById(elementId);
  if (!element) return;
  element.textContent = message;
}

function clearFieldError(elementId) {
  const element = document.getElementById(elementId);
  if (!element) return;
  element.textContent = '';
}

function clearFormErrors(ids) {
  ids.forEach((id) => {
    const element = document.getElementById(id);
    if (!element) return;

    const text = element.querySelector('.form-error__text');
    if (text) text.textContent = '';
    element.classList.remove('is-visible');
  });
}

function clearAllAuthErrors() {
  [
    'loginEmailError',
    'loginPasswordError',
    'registerUsernameError',
    'registerEmailError',
    'registerPasswordError'
  ].forEach(clearFieldError);

  ['loginFormError', 'registerFormError'].forEach((id) => {
    const element = document.getElementById(id);
    if (!element) return;

    const text = element.querySelector('.form-error__text');
    if (text) text.textContent = '';
    element.classList.remove('is-visible');
  });
}
