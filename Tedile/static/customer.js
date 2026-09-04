const state = {
  services: [],
  offset: 0,
  limit: 20,
  total: 0,
  selectedService: '',
  searchLocation: null,
  searchLocationLabel: null,
  bookingLocation: null,
  bookingLocationLabel: null,
  sort: 'rating-high',
  keyword: '',
  loading: false,
};
function setSearchLocation(location, label) {
  state.searchLocation = location;
  state.searchLocationLabel = label || location.city || 'your selected location';
}

function setBookingLocation(location, label) {
  state.bookingLocation = location;
  state.bookingLocationLabel = label || location.city || 'your service location';
}

const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
const providerInitials = (name) => {
  const initials = String(name || '').trim().split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
  return initials || 'Tedile';
};
const iconFor = (service) => escapeHtml(service.icon_key || 'spark');

async function loadServices() {
  const response = await fetch('/api/services');
  if (!response.ok) throw new Error('Unable to load services.');
  const payload = await response.json();
  state.services = (payload.data || []).filter((service) => service.is_active !== false).sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
  renderServices();
}

function serviceCard(service) {
  return `<button class="service-card" type="button" data-service="${escapeHtml(service.slug)}" aria-label="Search ${escapeHtml(service.name)}"><span class="service-icon" data-icon-key="${iconFor(service)}" aria-hidden="true">✦</span><span>${escapeHtml(service.name)}</span></button>`;
}

function renderServices() {
  const popular = document.getElementById('popular-services');
  const groups = document.getElementById('service-groups');
  if (!popular || !groups) return;
  popular.innerHTML = state.services.slice(0, 8).map(serviceCard).join('');
  const grouped = new Map();
  state.services.forEach((service) => {
    const key = service.display_group || 'More services';
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(service);
  });
  groups.innerHTML = [...grouped.entries()].map(([name, services]) => `<section class="service-group"><div class="group-heading"><h3>${escapeHtml(name)}</h3><span>${services.length} services</span></div><div class="service-rail">${services.map(serviceCard).join('')}</div></section>`).join('');
  document.querySelectorAll('[data-service]').forEach((button) => button.addEventListener('click', () => {
    state.selectedService = button.dataset.service;
    document.getElementById('hero-search-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    searchProviders(true);
  }));
}

async function resolveLocation(query) {
  if (!query.trim()) return null;
  const response = await fetch(`/api/search/geocode?q=${encodeURIComponent(query.trim())}`);
  if (!response.ok) throw new Error('We could not find that location.');
  const payload = await response.json();
  return payload.data?.[0] || null;
}

function renderSkeletons() {
  const target = document.getElementById('provider-results');
  if (target) target.innerHTML = Array.from({ length: 4 }, () => '<div class="provider-card skeleton-card"><div class="skeleton-photo"></div><div class="skeleton-line wide"></div><div class="skeleton-line"></div><div class="skeleton-line short"></div></div>').join('');
}

function attachImageErrorFallbacks(root) {
  root.querySelectorAll('[data-image-fallback]').forEach((image) => {
    if (image.dataset.imageFallbackBound) return;
    image.dataset.imageFallbackBound = 'true';
    image.addEventListener('error', () => {
      image.hidden = true;
      if (image.nextElementSibling) image.nextElementSibling.hidden = false;
    }, { once: true });
  });
}

function providerCard(provider) {
  const photo = provider.profile_photo_url ? `<img loading="lazy" src="${escapeHtml(provider.profile_photo_url)}" alt="" class="provider-photo" data-image-fallback /><div class="photo-fallback" hidden aria-hidden="true">${escapeHtml((provider.name || '?').slice(0, 1))}</div>` : `<div class="photo-fallback" aria-hidden="true">${escapeHtml((provider.name || '?').slice(0, 1))}</div>`;
  const canBook = provider.availability === 'available';
  const action = canBook ? `<a class="button button-secondary full-button" href="/providers/${encodeURIComponent(provider.id)}">View profile</a>` : `<span class="button button-secondary full-button" aria-disabled="true">Unavailable for new bookings</span>`;
  const directions = state.searchLocation ? `<button class="button button-quiet full-button" type="button" data-directions-provider="${escapeHtml(provider.id)}">Get Directions</button>` : '';
  return `<article class="provider-card"><div class="provider-card-top">${photo}<span class="availability ${canBook ? 'is-available' : ''}">${escapeHtml(provider.availability || 'offline')}</span></div><div class="provider-card-body"><div class="provider-name-row"><h3>${escapeHtml(provider.name)}</h3>${provider.verified ? '<span class="verified-mark" title="Verified provider">✓</span>' : ''}</div><p class="provider-location">${escapeHtml([provider.city, provider.state].filter(Boolean).join(', '))}</p><div class="provider-stats"><span>★ ${escapeHtml(provider.rating || '—')}</span><span>${escapeHtml(provider.reviews_count || 0)} reviews</span></div><div class="provider-meta"><span>${escapeHtml(provider.experience_years || 0)} yrs experience</span><span>${escapeHtml(provider.jobs_completed || 0)} jobs</span></div><div class="provider-card-footer"><strong>${provider.hourly_rate != null ? `₹${escapeHtml(provider.hourly_rate)}/hr` : 'Rate on request'}</strong><span class="distance-badge">${escapeHtml(provider.distance_bucket || 'Nearby')}</span></div>${action}${directions}</div></article>`;
}

function attachDirections() {
  document.querySelectorAll('[data-directions-provider]').forEach(button => button.addEventListener('click', async () => {
    const params = new URLSearchParams({ latitude: state.searchLocation.latitude, longitude: state.searchLocation.longitude });
    const response = await fetch(`/api/providers/${encodeURIComponent(button.dataset.directionsProvider)}/directions?${params}`);
    const payload = await response.json();
    if (response.ok && payload.url) window.open(payload.url, '_blank', 'noopener');
  }));
}

function renderResults(providers, append = false) {
  const target = document.getElementById('provider-results');
  if (!target) return;
  const html = providers.map(providerCard).join('');
  if (append) target.insertAdjacentHTML('beforeend', html); else target.innerHTML = html || '<div class="empty-state wide-empty"><span class="empty-mark">⌕</span><h3>No providers found yet.</h3><p>Try another service, location, or a broader search.</p></div>';
  attachImageErrorFallbacks(target);
  attachDirections();
}

async function searchProviders(reset = false) {
  if (state.loading) return;
  if (reset) state.offset = 0;
  state.loading = true;
  if (!reset && state.offset === 0) renderSkeletons();
  const params = new URLSearchParams({ limit: String(state.limit), offset: String(state.offset), sort: state.sort });
  if (state.keyword) params.set('keyword', state.keyword);
  if (state.selectedService) params.set('service', state.selectedService);
  if (state.searchLocation) {
    params.set('latitude', state.searchLocation.latitude);
    params.set('longitude', state.searchLocation.longitude);
  }
  try {
    const response = await fetch(`/api/search/providers?${params}`);
    if (!response.ok) throw new Error('Search is temporarily unavailable.');
    const payload = await response.json();
    state.total = payload.total || 0;
    renderResults(payload.data?.providers || [], !reset && state.offset > 0);
    state.offset = payload.next_offset ?? state.total;
    const more = document.getElementById('load-more');
    if (more) more.hidden = payload.next_offset == null;
    const status = document.getElementById('hero-status');
    if (status) status.textContent = state.searchLocation ? `Showing providers near ${state.searchLocationLabel || state.searchLocation.city || 'your selected location'}` : `${state.total} providers found`;
  } catch (error) {
    const target = document.getElementById('provider-results');
    if (target) target.innerHTML = `<div class="error-state wide-empty"><h3>We hit a snag.</h3><p>${escapeHtml(error.message)}</p><button class="button button-secondary" id="retry-search" type="button">Try again</button></div>`;
    document.getElementById('retry-search')?.addEventListener('click', () => searchProviders(true));
  } finally { state.loading = false; }
}

async function loadProfile() {
  const target = document.getElementById('provider-profile');
  if (!target) return;
  try {
    const response = await fetch(`/api/providers/${encodeURIComponent(target.dataset.profileCode)}`);
    if (!response.ok) throw new Error('Provider profile not found.');
    const provider = await response.json();
    const photo = provider.profile_photo_url ? `<img class="profile-photo" loading="lazy" src="${escapeHtml(provider.profile_photo_url)}" alt="" data-image-fallback />` : `<div class="profile-photo photo-fallback" role="img" aria-label="Provider avatar">${escapeHtml(providerInitials(provider.name))}</div>`;
    target.innerHTML = `<div class="profile-card"><div class="profile-visual">${photo}</div><div class="profile-content"><p class="eyebrow">LOCAL PROFESSIONAL</p><h1>${escapeHtml(provider.name)} ${provider.verified ? '<span class="verified-mark">✓</span>' : ''}</h1><p class="provider-location">${escapeHtml([provider.city, provider.state].filter(Boolean).join(', '))}</p><div class="profile-stats"><span>★ ${escapeHtml(provider.rating || '—')} · ${escapeHtml(provider.reviews_count || 0)} reviews</span><span>${escapeHtml(provider.experience_years || 0)} years experience</span><span>${escapeHtml(provider.jobs_completed || 0)} jobs completed</span></div><div class="profile-rate">${provider.hourly_rate != null ? `₹${escapeHtml(provider.hourly_rate)} / hour` : 'Rate on request'}</div><button class="button button-primary" type="button" id="start-booking">Request this provider</button><p class="profile-note">Contact details are shared only after an authorized booking is confirmed.</p></div></div><div class="booking-panel" id="booking-panel" hidden><p class="eyebrow">BOOK A VISIT</p><h2>Tell us when you need help.</h2><form id="booking-form"><label>Date and time<input type="datetime-local" name="scheduled_at" required /></label><label>Notes<textarea name="notes" rows="4" placeholder="Add helpful details about the job"></textarea></label><input type="hidden" name="provider_profile_code" value="${escapeHtml(provider.id)}" /><label>Service<select name="service_slug" id="booking-service" required><option value="">Loading services…</option></select></label><fieldset class="booking-location"><legend>Service location</legend><button class="button button-quiet" type="button" id="use-booking-current-location">Use my current location</button><button class="button button-quiet" type="button" id="use-booking-search-location">Use selected search location</button><p class="form-status" id="booking-location-status"></p></fieldset><button class="button button-primary" type="submit">Send booking request</button><p class="form-status" id="booking-status"></p></form></div>`;
    attachImageErrorFallbacks(target);
    const bookingService = document.getElementById('booking-service');
if (bookingService) {
  const serviceResponse = await fetch(`/api/providers/${encodeURIComponent(provider.id)}/services`);
  if (!serviceResponse.ok) throw new Error('Unable to load provider services.');
  const servicePayload = await serviceResponse.json();
  const providerServices = servicePayload.data || [];

  bookingService.innerHTML = providerServices.length
    ? providerServices.map((service) => `<option value="${escapeHtml(service.slug)}">${escapeHtml(service.name)}</option>`).join('')
    : '<option value="">No services available</option>';
}
    document.getElementById('start-booking')?.addEventListener('click', () => { document.getElementById('booking-panel').hidden = false; });
    document.getElementById('booking-form')?.addEventListener('submit', submitBooking);
    document.getElementById('use-booking-current-location')?.addEventListener('click', requestBookingLocation);
    document.getElementById('use-booking-search-location')?.addEventListener('click', () => {
      if (state.searchLocation) {
        setBookingLocation(state.searchLocation, state.searchLocationLabel || state.searchLocation.city || 'Selected search location');
        updateBookingLocationStatus('Using the selected search location for this booking.');
      } else updateBookingLocationStatus('Search for a location first or use your current location.');
    });
  } catch (error) { target.innerHTML = `<div class="error-state wide-empty"><h2>${escapeHtml(error.message)}</h2><a class="button button-secondary" href="/">Back to search</a></div>`; }
}

function updateBookingLocationStatus(message) {
  const status = document.getElementById('booking-location-status');
  if (status) status.textContent = message;
}

function requestBookingLocation() {
  if (!navigator.geolocation) {
    updateBookingLocationStatus('Current location is unavailable. Use the selected search location.');
    return;
  }
  updateBookingLocationStatus('Requesting your current location…');
  navigator.geolocation.getCurrentPosition((position) => {
    setBookingLocation({ latitude: position.coords.latitude, longitude: position.coords.longitude }, 'Your current location');
    updateBookingLocationStatus('Using your current location for this booking.');
  }, () => updateBookingLocationStatus('Location access was unavailable. Use the selected search location.'), { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
}

async function submitBooking(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById('booking-status');
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
  const data = new FormData(form);
  if (state.bookingLocation) {
    data.set('customer_latitude', state.bookingLocation.latitude);
    data.set('customer_longitude', state.bookingLocation.longitude);
    data.set('customer_location_label', state.bookingLocationLabel || state.bookingLocation.city || 'Selected location');
  }
  if (!state.bookingLocation) {
    status.textContent = 'Choose a service location before booking.';
    return;
  }
  const response = await fetch('/customer/bookings', { method: 'POST', body: data, headers: csrf ? { 'X-CSRFToken': csrf } : {} });
if (response.ok) {
  status.textContent = 'Booking request sent successfully. Check your bookings for status updates.';
} else {
  const payload = await response.json().catch(() => ({}));
  status.textContent = payload.error || 'Unable to send booking request.';
}}

function attachCancellation() {
  document.querySelectorAll('.cancel-booking').forEach((button) => button.addEventListener('click', async () => {
    if (!window.confirm('Are you sure you want to cancel this booking?')) return;
    const error = button.parentElement.querySelector('.booking-error');
    button.disabled = true;
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
    try {
      const response = await fetch(button.dataset.cancelUrl, { method: 'POST', headers: csrf ? { 'X-CSRFToken': csrf } : {}, credentials: 'same-origin' });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || 'Unable to cancel this booking.');
      const pill = button.parentElement.querySelector('.status-pill');
      pill.textContent = 'cancelled';
      pill.className = 'status-pill status-cancelled';
      button.remove();
    } catch (err) {
      button.disabled = false;
      error.textContent = err.message;
      error.hidden = false;
    }
  }));
}

document.addEventListener('DOMContentLoaded', () => {
  loadServices().catch(() => { const groups = document.getElementById('service-groups'); if (groups) groups.innerHTML = '<div class="error-state">Unable to load services.</div>'; });
  const form = document.getElementById('hero-search-form');
  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    state.keyword = document.getElementById('hero-keyword')?.value.trim() || '';
    const status = document.getElementById('hero-status');
    try {
      const location = await resolveLocation(document.getElementById('hero-location')?.value || '');
      if (!location) throw new Error('We could not find that location.');
      setSearchLocation(location);
      await searchProviders(true);
      document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
      if (status) status.textContent = error.message || 'We could not find that location.';
    }
  });
  document.getElementById('use-current-location')?.addEventListener('click', () => {
    const status = document.getElementById('hero-status');
    if (!navigator.geolocation) {
      if (status) status.textContent = 'Location is unavailable in this browser. You can search for a location manually.';
      return;
    }
    if (status) status.textContent = 'Requesting your current location…';
    navigator.geolocation.getCurrentPosition(async position => {
      const gpsLocation = { latitude: position.coords.latitude, longitude: position.coords.longitude };
      setSearchLocation(gpsLocation, 'Your current location');
      setBookingLocation(gpsLocation, 'Your current location');
      const input = document.getElementById('hero-location');
      if (input) input.value = 'Current location';
      await searchProviders(true);
      document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' });
    }, error => {
      const message = error.code === 1
        ? 'Location access was denied. You can search for a location manually.'
        : error.code === 3
          ? 'Location request timed out. You can search for a location manually.'
          : 'We could not determine your location. You can search for a location manually.';
      if (status) status.textContent = message;
    }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
  });
  document.getElementById('sort-select')?.addEventListener('change', (event) => { state.sort = event.target.value; searchProviders(true); });
  document.getElementById('load-more')?.addEventListener('click', () => searchProviders(false));
  document.getElementById('view-all-services')?.addEventListener('click', () => document.getElementById('service-groups')?.scrollIntoView({ behavior: 'smooth' }));
  if (document.getElementById('provider-results')) searchProviders(true);
  loadProfile();
  attachCancellation();
});
