const state = {
  services: [],
  offset: 0,
  limit: 20,
  total: 0,
  selectedService: '',
  selectedLocation: null,
  sort: 'rating-high',
  keyword: '',
  loading: false,
};

const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
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
  return `<article class="provider-card"><div class="provider-card-top">${photo}<span class="availability ${provider.availability === 'available' ? 'is-available' : ''}">${escapeHtml(provider.availability || 'offline')}</span></div><div class="provider-card-body"><div class="provider-name-row"><h3>${escapeHtml(provider.name)}</h3>${provider.verified ? '<span class="verified-mark" title="Verified provider">✓</span>' : ''}</div><p class="provider-location">${escapeHtml([provider.city, provider.state].filter(Boolean).join(', '))}</p><div class="provider-stats"><span>★ ${escapeHtml(provider.rating || '—')}</span><span>${escapeHtml(provider.reviews_count || 0)} reviews</span></div><div class="provider-meta"><span>${escapeHtml(provider.experience_years || 0)} yrs experience</span><span>${escapeHtml(provider.jobs_completed || 0)} jobs</span></div><div class="provider-card-footer"><strong>${provider.hourly_rate != null ? `₹${escapeHtml(provider.hourly_rate)}/hr` : 'Rate on request'}</strong><span class="distance-badge">${escapeHtml(provider.distance_bucket || 'Nearby')}</span></div><a class="button button-secondary full-button" href="/providers/${encodeURIComponent(provider.id)}">View profile</a></div></article>`;
}

function renderResults(providers, append = false) {
  const target = document.getElementById('provider-results');
  if (!target) return;
  const html = providers.map(providerCard).join('');
  if (append) target.insertAdjacentHTML('beforeend', html); else target.innerHTML = html || '<div class="empty-state wide-empty"><span class="empty-mark">⌕</span><h3>No providers found yet.</h3><p>Try another service, location, or a broader search.</p></div>';
  attachImageErrorFallbacks(target);
}

async function searchProviders(reset = false) {
  if (state.loading) return;
  if (reset) state.offset = 0;
  state.loading = true;
  if (!reset && state.offset === 0) renderSkeletons();
  const params = new URLSearchParams({ limit: String(state.limit), offset: String(state.offset), sort: state.sort });
  if (state.keyword) params.set('keyword', state.keyword);
  if (state.selectedService) params.set('service', state.selectedService);
  if (state.selectedLocation) {
    params.set('latitude', state.selectedLocation.latitude);
    params.set('longitude', state.selectedLocation.longitude);
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
    if (status) status.textContent = `${state.total} providers found`;
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
    const photo = provider.profile_photo_url ? `<img class="profile-photo" loading="lazy" src="${escapeHtml(provider.profile_photo_url)}" alt="" data-image-fallback />` : '<div class="profile-photo photo-fallback">?</div>';
    target.innerHTML = `<div class="profile-card"><div class="profile-visual">${photo}</div><div class="profile-content"><p class="eyebrow">LOCAL PROFESSIONAL</p><h1>${escapeHtml(provider.name)} ${provider.verified ? '<span class="verified-mark">✓</span>' : ''}</h1><p class="provider-location">${escapeHtml([provider.city, provider.state].filter(Boolean).join(', '))}</p><div class="profile-stats"><span>★ ${escapeHtml(provider.rating || '—')} · ${escapeHtml(provider.reviews_count || 0)} reviews</span><span>${escapeHtml(provider.experience_years || 0)} years experience</span><span>${escapeHtml(provider.jobs_completed || 0)} jobs completed</span></div><div class="profile-rate">${provider.hourly_rate != null ? `₹${escapeHtml(provider.hourly_rate)} / hour` : 'Rate on request'}</div><button class="button button-primary" type="button" id="start-booking">Request this provider</button><p class="profile-note">Contact details are shared only after an authorized booking is confirmed.</p></div></div><div class="booking-panel" id="booking-panel" hidden><p class="eyebrow">BOOK A VISIT</p><h2>Tell us when you need help.</h2><form id="booking-form"><label>Date and time<input type="datetime-local" name="scheduled_at" required /></label><label>Notes<textarea name="notes" rows="4" placeholder="Add helpful details about the job"></textarea></label><input type="hidden" name="provider_profile_code" value="${escapeHtml(provider.id)}" /><label>Service<select name="service_slug" id="booking-service" required><option value="">Loading services…</option></select></label><button class="button button-primary" type="submit">Send booking request</button><p class="form-status" id="booking-status"></p></form></div>`;
    attachImageErrorFallbacks(target);
    const bookingService = document.getElementById('booking-service');
    if (bookingService) bookingService.innerHTML = state.services.filter((service) => service.is_active !== false).map((service) => `<option value="${escapeHtml(service.slug)}">${escapeHtml(service.name)}</option>`).join('');
    document.getElementById('start-booking')?.addEventListener('click', () => { document.getElementById('booking-panel').hidden = false; });
    document.getElementById('booking-form')?.addEventListener('submit', submitBooking);
  } catch (error) { target.innerHTML = `<div class="error-state wide-empty"><h2>${escapeHtml(error.message)}</h2><a class="button button-secondary" href="/">Back to search</a></div>`; }
}

async function submitBooking(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById('booking-status');
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
  const response = await fetch('/customer/bookings', { method: 'POST', body: new FormData(form), headers: csrf ? { 'X-CSRFToken': csrf } : {} });
  status.textContent = response.ok ? 'Request sent. Log in to follow its status.' : 'Please log in before sending a booking request.';
}

document.addEventListener('DOMContentLoaded', () => {
  loadServices().catch(() => { const groups = document.getElementById('service-groups'); if (groups) groups.innerHTML = '<div class="error-state">Unable to load services.</div>'; });
  const form = document.getElementById('hero-search-form');
  form?.addEventListener('submit', async (event) => { event.preventDefault(); state.keyword = document.getElementById('hero-keyword')?.value.trim() || ''; state.selectedLocation = await resolveLocation(document.getElementById('hero-location')?.value || ''); searchProviders(true); document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' }); });
  document.getElementById('sort-select')?.addEventListener('change', (event) => { state.sort = event.target.value; searchProviders(true); });
  document.getElementById('load-more')?.addEventListener('click', () => searchProviders(false));
  document.getElementById('view-all-services')?.addEventListener('click', () => document.getElementById('service-groups')?.scrollIntoView({ behavior: 'smooth' }));
  if (document.getElementById('provider-results')) searchProviders(true);
  loadProfile();
});
