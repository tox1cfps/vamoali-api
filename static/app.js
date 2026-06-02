// ===== CONFIG =====
const API_URL = '';

// ===== STATE =====
let currentUser = null;
let currentToken = null;
let places = [];
let currentFeedbackPlaceId = null;
let currentFilter = 'all';
let currentSearch = '';
let currentResetToken = null;
const visitedOverrides = new Map();
const favoriteOverrides = new Map();
const visitedRequestTokens = new Map();
let visitedRequestCounter = 0;

// ===== INIT =====
document.addEventListener('DOMContentLoaded', init);

function init() {
  bindEvents();
  loadPublicConfig();
  openPasswordResetFromLink();
  applyStoredTheme();
  restoreSession();
}

async function loadPublicConfig() {
  const resetButton = document.getElementById('resetPasswordButton');
  if (!resetButton) return;

  try {
    const response = await fetch(`${API_URL}/config`);
    const config = await response.json();
    resetButton.hidden = !config.enable_password_reset;
  } catch (error) {
    resetButton.hidden = true;
  }
}

function openPasswordResetFromLink() {
  const params = new URLSearchParams(window.location.search);
  const resetToken = params.get('reset_token');
  if (!resetToken) return;

  currentResetToken = resetToken;
  document.getElementById('resetNewPassword').value = '';
  openModal('resetPasswordConfirmModal');
  window.history.replaceState({}, document.title, window.location.pathname);
}

function handleSearch(event) {
  currentSearch = event.target.value.trim().toLowerCase();
  renderPlaces();
}

function bindEvents() {
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const addPlaceForm = document.getElementById('addPlaceForm');
  const feedbackForm = document.getElementById('feedbackForm');
  const resetPasswordRequestForm = document.getElementById('resetPasswordRequestForm');
  const resetPasswordConfirmForm = document.getElementById('resetPasswordConfirmForm');
  const themeToggle = document.getElementById('themeToggle');
  const searchInput = document.getElementById('navbarSearch');
  if (searchInput) searchInput.addEventListener('input', handleSearch);

  if (loginForm) loginForm.addEventListener('submit', handleLogin);
  if (registerForm) registerForm.addEventListener('submit', handleRegister);
  if (addPlaceForm) addPlaceForm.addEventListener('submit', handleAddPlace);
  if (feedbackForm) feedbackForm.addEventListener('submit', handleAddFeedback);
  if (resetPasswordRequestForm) resetPasswordRequestForm.addEventListener('submit', handleResetPasswordRequest);
  if (resetPasswordConfirmForm) resetPasswordConfirmForm.addEventListener('submit', handleResetPasswordConfirm);
  if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
}

function restoreSession() {
  // Não redireciona se já está na página de autenticação
  if (window.location.pathname.includes('auth.html')) {
    return;
  }

  const token = localStorage.getItem('token');
  const user = localStorage.getItem('user');

  if (!token || !user) {
    window.location.href = 'auth.html';
    return;
  }

  try {
    currentToken = token;
    currentUser = JSON.parse(user);
    syncUserHeader();
    loadPlaces();
  } catch (error) {
    logout();
  }
}

// ===== NAVIGATION =====

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
      const loginFormEl = document.getElementById('loginForm');
      loginFormEl.classList.remove('shake');
      void loginFormEl.offsetWidth;
      loginFormEl.classList.add('shake');
      setTimeout(() => loginFormEl.classList.remove('shake'), 500);
      return;
    }

    currentToken = data.token;
    currentUser = data.user;
    localStorage.setItem('token', currentToken);
    localStorage.setItem('user', JSON.stringify(currentUser));

    document.getElementById('loginForm').reset();
    window.location.href = 'places.html';
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
      const registerFormEl = document.getElementById('registerForm');
      registerFormEl.classList.remove('shake');
      void registerFormEl.offsetWidth;
      registerFormEl.classList.add('shake');
      setTimeout(() => registerFormEl.classList.remove('shake'), 500);
      return;
    }

    currentToken = data.token;
    currentUser = data.user;
    localStorage.setItem('token', currentToken);
    localStorage.setItem('user', JSON.stringify(currentUser));

    document.getElementById('registerForm').reset();
    window.location.href = 'places.html';
  } catch (error) {
    showError('registerFormError', 'Erro de conexão com a API.');
  }
}

function logout() {
  currentUser = null;
  currentToken = null;
  places = [];
  currentFeedbackPlaceId = null;
  currentResetToken = null;

  localStorage.removeItem('token');
  localStorage.removeItem('user');

  window.location.href = 'auth.html';
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
  const category = document.getElementById('placeCategory')?.value || '';

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
    feedback: '',
    category,
    favorited: false,
    rating: ''
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
      body: JSON.stringify({ name, maps_url: mapsUrl, photo_url: photoUrl, category })
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

async function toggleFavorite(placeId) {
  const place = getPlaceById(placeId);
  if (!place) return;

  const previousFavorite = normalizeBoolean(place.favorited);
  const nextFavorite = !previousFavorite;

  favoriteOverrides.set(String(placeId), nextFavorite);
  place.favorited = nextFavorite;
  renderPlaces();

  try {
    const response = await fetch(`${API_URL}/places/${encodeURIComponent(placeId)}/favorite`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${currentToken}` }
    });

    const data = await safeJson(response);

    if (!response.ok) {
      favoriteOverrides.delete(String(placeId));
      place.favorited = previousFavorite;
      renderPlaces();
      showToast(data.message || 'Erro ao favoritar lugar.', 'error');
      return;
    }

    favoriteOverrides.delete(String(placeId));
    showToast(nextFavorite ? 'Lugar favorito!' : 'Favorito removido.', 'success');
  } catch (error) {
    favoriteOverrides.delete(String(placeId));
    place.favorited = previousFavorite;
    renderPlaces();
    showToast('Erro ao favoritar lugar.', 'error');
  }
}

async function pickRandomPlace() {
  try {
    const response = await fetch(`${API_URL}/places/random`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });

    const data = await safeJson(response);

    if (!response.ok) {
      showToast(data.message || 'Não foi possível sortear um lugar.', 'error');
      return;
    }

    showToast(`Sorteado: ${data.name}`, 'info');
    highlightPlace(data.id);
  } catch (error) {
    showToast('Erro ao sortear lugar.', 'error');
  }
}

function highlightPlace(placeId) {
  const selector = `.place-card[data-id="${CSS.escape(String(placeId))}"]`;
  const card = document.querySelector(selector);
  if (!card) return;

  card.classList.add('place-card--highlight');
  card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  setTimeout(() => card.classList.remove('place-card--highlight'), 2400);
}

function updatePlaceCardUI(button, isVisited) {
  if (!button) return;
  const card = button.closest('.place-card');
  if (!card) return;

  const badge = card.querySelector('.place-card__badge');
  const feedbackButton = card.querySelector('.action-button--feedback');

  if (badge) {
    badge.textContent = isVisited ? 'Visitado' : 'Na lista';
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

let pendingDeleteId = null;
let pendingDeleteButton = null;

function deletePlace(placeId, button) {
  pendingDeleteId = placeId;
  pendingDeleteButton = button;
  openModal('confirmDeleteModal');
  document.getElementById('confirmDeleteBtn').onclick = async () => {
    closeModal('confirmDeleteModal');
    const previousPlaces = places.slice();
    places = places.filter((place) => String(place.id) !== String(pendingDeleteId));
    renderPlaces();
    try {
      const response = await fetch(`${API_URL}/places/${encodeURIComponent(pendingDeleteId)}`, {
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
    pendingDeleteId = null;
    pendingDeleteButton = null;
  };
}

// ===== FEEDBACK =====
function openFeedbackModal(placeId) {
  currentFeedbackPlaceId = placeId;
  clearFormErrors(['feedbackTextError', 'feedbackRatingError', 'feedbackFormError']);

  const place = getPlaceById(placeId);
  const feedbackInput = document.getElementById('feedbackText');
  const feedbackRatingInput = document.getElementById('feedbackRatingValue');
  if (feedbackInput) {
    feedbackInput.value = place?.feedback ? String(place.feedback) : '';
  }
  if (feedbackRatingInput) {
    feedbackRatingInput.value = place?.rating ? String(place.rating) : '';
  }

  openModal('feedbackModal');
}

async function handleResetPasswordRequest(event) {
  event.preventDefault();
  clearFormErrors(['resetEmailError', 'resetRequestFormError']);

  const email = document.getElementById('resetEmail').value.trim();

  if (!email) {
    showFieldError('resetEmailError', 'Informe o email.');
    return;
  }

  try {
    const response = await fetch(`${API_URL}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });

    const data = await safeJson(response);

    if (!response.ok) {
      showError('resetRequestFormError', data.message || 'Erro ao solicitar redefinição.');
      return;
    }

    closeModal('resetPasswordRequestModal');
    showToast(data.message || 'Se a conta existir, enviaremos instruções por email.', 'info');
  } catch (error) {
    showError('resetRequestFormError', 'Erro ao solicitar redefinição.');
  }
}

async function handleResetPasswordConfirm(event) {
  event.preventDefault();
  clearFormErrors(['resetNewPasswordError', 'resetConfirmFormError']);

  const newPassword = document.getElementById('resetNewPassword').value;

  if (!currentResetToken) {
    showError('resetConfirmFormError', 'Solicite um novo link de redefinição.');
    return;
  }

  if (!newPassword) {
    showFieldError('resetNewPasswordError', 'Informe a nova senha.');
    return;
  }

  try {
    const response = await fetch(`${API_URL}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: currentResetToken, new_password: newPassword })
    });

    const data = await safeJson(response);

    if (!response.ok) {
      showError('resetConfirmFormError', data.message || 'Erro ao redefinir senha.');
      return;
    }

    currentResetToken = null;
    closeModal('resetPasswordConfirmModal');
    showToast('Senha redefinida com sucesso!', 'success');
  } catch (error) {
    showError('resetConfirmFormError', 'Erro ao redefinir senha.');
  }
}

async function handleAddFeedback(event) {
  event.preventDefault();
  clearFormErrors(['feedbackTextError', 'feedbackRatingError', 'feedbackFormError']);

  const feedback = document.getElementById('feedbackText').value.trim();
  const rating = document.getElementById('feedbackRatingValue').value;

  if (!currentFeedbackPlaceId) {
    showError('feedbackFormError', 'Selecione um lugar primeiro.');
    return;
  }

  if (!feedback) {
    showFieldError('feedbackTextError', 'Escreva um feedback.');
    return;
  }

  if (!rating) {
    showFieldError('feedbackRatingError', 'Selecione uma nota.');
    return;
  }

  try {
    const feedbackResponse = await fetch(`${API_URL}/places/${encodeURIComponent(currentFeedbackPlaceId)}/feedback`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${currentToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ feedback })
    });

    const feedbackData = await safeJson(feedbackResponse);

    if (!feedbackResponse.ok) {
      showError('feedbackFormError', feedbackData.message || 'Erro ao salvar feedback.');
      return;
    }

    const ratingResponse = await fetch(`${API_URL}/places/${encodeURIComponent(currentFeedbackPlaceId)}/rating`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${currentToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ rating })
    });

    const ratingData = await safeJson(ratingResponse);

    if (!ratingResponse.ok) {
      showError('feedbackFormError', ratingData.message || 'Feedback salvo, mas a nota não foi atualizada.');
      return;
    }

    document.getElementById('feedbackForm').reset();
    closeModal('feedbackModal');
    await loadPlaces();
    showToast('Feedback e nota salvos com sucesso!', 'success');
  } catch (error) {
    showError('feedbackFormError', 'Erro ao salvar feedback e nota.');
  }
}

// ===== RENDERING =====
function setFilter(filter) {
  currentFilter = filter;
  document.querySelectorAll('.places-tab').forEach((btn) => {
    btn.classList.toggle('places-tab--active', btn.dataset.filter === filter);
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
  const matchesSearch = (place) => {
    if (!currentSearch) return true;
    const name = (place.name || '').toLowerCase();
    const category = (place.category || '').toLowerCase();
    return name.includes(currentSearch) || category.includes(currentSearch);
  };

  const pending = places
    .filter(p => !normalizeVisited(p.visited) && matchesSearch(p))
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  
  const visited = places
    .filter(p => normalizeVisited(p.visited) && matchesSearch(p))
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));

  const favorites = places
    .filter((place) => {
      const override = favoriteOverrides.get(String(place.id));
      const isFavorite = typeof override === 'boolean' ? override : normalizeBoolean(place.favorited);
      return isFavorite && matchesSearch(place);
    })
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));

  // Filter based on current filter
  let sectionsToShow = [];
  
  if (currentFilter === 'all') {
    if (pending.length > 0) sectionsToShow.push({ title: 'Para visitar', count: pending.length, places: pending });
    if (visited.length > 0) sectionsToShow.push({ title: 'Já visitamos', count: visited.length, places: visited });
  } else if (currentFilter === 'pending') {
    if (pending.length > 0) sectionsToShow.push({ title: 'Para visitar', count: pending.length, places: pending });
  } else if (currentFilter === 'visited') {
    if (visited.length > 0) sectionsToShow.push({ title: 'Já visitamos', count: visited.length, places: visited });
  } else if (currentFilter === 'favorites') {
    if (favorites.length > 0) sectionsToShow.push({ title: 'Favoritos', count: favorites.length, places: favorites });
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
  const favoriteOverride = favoriteOverrides.get(String(place.id ?? safeId));
  const isFavorite = typeof favoriteOverride === 'boolean' ? favoriteOverride : normalizeBoolean(place.favorited);
  const badgeClass = isVisited ? 'place-card__badge--visited' : 'place-card__badge--pending';
  const badgeText = isVisited ? 'Visitado' : 'Na lista';
  const feedback = place.feedback ? `<p class="place-card__feedback">"${escapeHtml(place.feedback)}"</p>` : '';
  const color = hashColor(String(place.name ?? place.id ?? 'V'));
  const feedbackDisabledAttr = !isVisited ? 'disabled aria-disabled="true" title="Marque como visitado primeiro"' : 'title="Feedback"';
  const visitedLabel = isVisited ? 'Visitado ✓' : '✓ Visitei';
  const visitedClass = isVisited ? 'is-visited' : '';
  const categoryBadge = place.category
    ? `<span class="place-card__category">${escapeHtml(place.category)}</span>`
    : '';
  const ratingValue = place.rating ? Number(place.rating) : 0;
  const ratingBadge = ratingValue ? `<span class="place-card__rating">⭐ ${ratingValue}</span>` : '';
  const favoriteLabel = isFavorite ? '♥' : '♡';
  const favoriteClass = isFavorite ? 'is-favorite' : '';

  if (photoUrl) {
    return `
      <article class="place-card place-card--with-photo" data-id="${safeId}">
        <img class="place-card__photo" src="${photoUrl}" alt="${name}" onerror="this.style.display='none';this.closest('.place-card').classList.remove('place-card--with-photo')">
        <div class="place-card__row">
          <div class="place-card__emoji" aria-hidden="true" style="background:${color};">${String((place.name||'')[0]||'V').toUpperCase()}</div>
          <div class="place-card__body">
            <h3 class="place-card__name">${name}</h3>
            ${categoryBadge}
            <div class="place-card__meta">
              <span class="place-card__badge ${badgeClass}">${badgeText}</span>
              ${ratingBadge}
              <a class="place-card__maps" href="${mapsUrl}" target="_blank" rel="noopener noreferrer">Ver no Maps →</a>
            </div>
            ${feedback}
          </div>
          <div class="place-card__actions">
            <button type="button" class="action-button action-button--favorite ${favoriteClass}" onclick="toggleFavorite('${safeId}')" title="Favoritar lugar">${favoriteLabel}</button>
            <button type="button" class="action-button action-button--visited ${visitedClass}" onclick="markAsVisited('${safeId}', this)" title="Marcar visitado">${visitedLabel}</button>
            <button type="button" class="action-button action-button--feedback" ${feedbackDisabledAttr} onclick="openFeedbackModal('${safeId}')">
              <img class="action-icon action-icon--feedback icon-tint-dark" src="feedback-svgrepo-com.svg" alt="">
            </button>
            <button type="button" class="action-button action-button--delete" onclick="deletePlace('${safeId}', this)" title="Excluir lugar">
              <img class="action-icon action-icon--delete icon-tint-dark" src="garbage-trash-svgrepo-com.svg" alt="">
            </button>
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
        ${categoryBadge}
        <div class="place-card__meta">
          <span class="place-card__badge ${badgeClass}">${badgeText}</span>
          ${ratingBadge}
          <a class="place-card__maps" href="${mapsUrl}" target="_blank" rel="noopener noreferrer">Ver no Maps →</a>
        </div>
        ${feedback}
      </div>
      <div class="place-card__actions">
        <button type="button" class="action-button action-button--favorite ${favoriteClass}" onclick="toggleFavorite('${safeId}')" title="Favoritar lugar">${favoriteLabel}</button>
        <button type="button" class="action-button action-button--visited ${visitedClass}" onclick="markAsVisited('${safeId}', this)" title="Marcar visitado">${visitedLabel}</button>
        <button type="button" class="action-button action-button--feedback" ${feedbackDisabledAttr} onclick="openFeedbackModal('${safeId}')">
          <img class="action-icon action-icon--feedback icon-tint-dark" src="feedback-svgrepo-com.svg" alt="">
        </button>
        <button type="button" class="action-button action-button--delete" onclick="deletePlace('${safeId}', this)" title="Excluir lugar">
          <img class="action-icon action-icon--delete icon-tint-dark" src="garbage-trash-svgrepo-com.svg" alt="">
        </button>
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

function normalizeBoolean(value) {
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
