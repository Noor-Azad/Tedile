(() => {
  const page = document.querySelector('.directions-page');
  const map = document.getElementById('directions-map');
  const status = document.getElementById('directions-status');
  const summary = document.getElementById('directions-summary');
  const steps = document.getElementById('directions-steps');
  let points;
  let zoom = 1;
  const query = new URLSearchParams(window.location.search);

  const number = (value) => Number(value);
  const valid = (latitude, longitude) => Number.isFinite(number(latitude)) && Number.isFinite(number(longitude)) && number(latitude) >= -90 && number(latitude) <= 90 && number(longitude) >= -180 && number(longitude) <= 180;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const meters = (value) => value >= 1000 ? `${(value / 1000).toFixed(1)} km` : `${Math.round(value)} m`;
  function render() {
    const provider = points.provider;
    const customer = points.customer;
    const geometry = points.route?.geometry?.coordinates?.length ? points.route.geometry.coordinates : [[customer.longitude, customer.latitude], [provider.longitude, provider.latitude]];
    const routePoints = geometry.map((point) => ({ latitude: number(point[1]), longitude: number(point[0]) })).filter((point) => valid(point.latitude, point.longitude));
    const all = [provider, customer, ...routePoints];
    const minLat = Math.min(...all.map((point) => point.latitude)), maxLat = Math.max(...all.map((point) => point.latitude));
    const minLon = Math.min(...all.map((point) => point.longitude)), maxLon = Math.max(...all.map((point) => point.longitude));
    const latSpan = Math.max(maxLat - minLat, 0.002), lonSpan = Math.max(maxLon - minLon, 0.002), pad = 140;
    const x = (longitude) => pad + ((longitude - minLon) / lonSpan) * (1000 - 2 * pad) * zoom;
    const y = (latitude) => 600 - pad - ((latitude - minLat) / latSpan) * (600 - 2 * pad) * zoom;
    const path = routePoints.map((point) => `${x(point.longitude)},${y(point.latitude)}`).join(' ');
    const customerX = x(customer.longitude), customerY = y(customer.latitude), providerX = x(provider.longitude), providerY = y(provider.latitude);
    map.innerHTML = `<div class="map-canvas"><div class="map-grid"></div><svg viewBox="0 0 1000 600" role="img" aria-label="Road route from your location to provider"><polyline points="${path}" class="route-line"/><circle cx="${customerX}" cy="${customerY}" r="18" class="customer-marker"/><circle cx="${providerX}" cy="${providerY}" r="18" class="provider-marker"/><text x="${customerX + 24}" y="${customerY - 20}" class="map-label">You</text><text x="${providerX + 24}" y="${providerY - 20}" class="map-label">Provider</text></svg></div>`;
    if (steps) steps.innerHTML = points.route?.steps?.length ? points.route.steps.map((step) => `<li>${esc(step.name ? `${step.maneuver?.type || 'Continue'} on ${step.name}` : (step.maneuver?.type || 'Continue'))} — ${meters(number(step.distance) || 0)}</li>`).join('') : '<li>Route steps are unavailable.</li>';
  }
  function load() {
    const profileCode = page.dataset.profileCode;
    const customerLatitude = number(query.get('latitude') ?? page.dataset.customerLatitude);
    const customerLongitude = number(query.get('longitude') ?? page.dataset.customerLongitude);
    if (!profileCode || !valid(customerLatitude, customerLongitude)) throw new Error('The customer location could not be displayed.');
    const params = new URLSearchParams({ latitude: customerLatitude, longitude: customerLongitude });
    fetch(`/customer/providers/${encodeURIComponent(profileCode)}/directions/route?${params}`, { credentials: 'same-origin' })
      .then((response) => response.json().then((payload) => ({ response, payload })))
      .then(({ response, payload }) => {
        if (!response.ok) throw new Error(payload.error || 'Directions unavailable.');
        if (!valid(payload.provider?.latitude, payload.provider?.longitude) || !valid(payload.customer?.latitude, payload.customer?.longitude)) throw new Error('The route coordinates are invalid.');
        points = { provider: { latitude: number(payload.provider.latitude), longitude: number(payload.provider.longitude) }, customer: { latitude: number(payload.customer.latitude), longitude: number(payload.customer.longitude) }, route: payload.route };
        render();
        if (payload.route?.available === false || !payload.route?.geometry?.coordinates?.length) {
          status.textContent = "Route unavailable. We couldn't calculate a road route right now.";
          summary.textContent = '';
          return;
        }
        const hours = Math.floor(payload.route.duration_seconds / 3600), minutes = Math.round((payload.route.duration_seconds % 3600) / 60);
        status.textContent = 'Route ready.';
        summary.textContent = `Road distance: ${(payload.route.distance_meters / 1000).toFixed(1)} km · Estimated travel time: ${hours ? `${hours} hr ` : ''}${minutes} min`;
      }).catch((error) => { status.textContent = error.message; summary.textContent = ''; if (!points) map.innerHTML = '<p class="map-fallback">This route is currently unavailable.</p>'; });
  }
  document.getElementById('zoom-in')?.addEventListener('click', () => { zoom = Math.min(3, zoom + 1); if (points) render(); });
  document.getElementById('zoom-out')?.addEventListener('click', () => { zoom = Math.max(1, zoom - 1); if (points) render(); });
  try { load(); } catch (error) { status.textContent = error.message; }
})();
