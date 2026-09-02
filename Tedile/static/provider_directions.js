(() => {
  const map = document.getElementById('directions-map');
  const status = document.getElementById('directions-status');
  const summary = document.getElementById('directions-summary');
  const steps = document.getElementById('directions-steps');
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
  const reference = location.pathname.split('/').slice(-2, -1)[0];
  let points;
  let zoom = 1;

  const valid = (p) => p && Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude)) && Number(p.latitude) >= -90 && Number(p.latitude) <= 90 && Number(p.longitude) >= -180 && Number(p.longitude) <= 180;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const meters = (value) => value >= 1000 ? `${(value / 1000).toFixed(1)} km` : `${Math.round(value)} m`;
  function render() {
    if (!valid(points?.provider) || !valid(points?.customer)) throw new Error('The booking location could not be displayed.');
    const a = { latitude: Number(points.provider.latitude), longitude: Number(points.provider.longitude) };
    const b = { latitude: Number(points.customer.latitude), longitude: Number(points.customer.longitude) };
    const geometry = points.route?.geometry?.coordinates || [[a.longitude, a.latitude], [b.longitude, b.latitude]];
    const routePoints = geometry.map((point) => ({ latitude: Number(point[1]), longitude: Number(point[0]) })).filter(valid);
    const all = [a, b, ...routePoints];
    const minLat = Math.min(...all.map((point) => point.latitude)), maxLat = Math.max(...all.map((point) => point.latitude));
    const minLon = Math.min(...all.map((point) => point.longitude)), maxLon = Math.max(...all.map((point) => point.longitude));
    const latSpan = Math.max(maxLat - minLat, 0.002), lonSpan = Math.max(maxLon - minLon, 0.002), pad = 140;
    const x = (lon) => pad + ((lon - minLon) / lonSpan) * (1000 - 2 * pad) * zoom;
    const y = (lat) => 600 - pad - ((lat - minLat) / latSpan) * (600 - 2 * pad) * zoom;
    const path = routePoints.map((point) => `${x(point.longitude)},${y(point.latitude)}`).join(' ');
    const ax = x(a.longitude), ay = y(a.latitude), bx = x(b.longitude), by = y(b.latitude);
    map.innerHTML = `<div class="map-canvas"><div class="map-grid"></div><svg viewBox="0 0 1000 600" role="img" aria-label="Road route from provider to customer"><polyline points="${path}" class="route-line"/><circle cx="${ax}" cy="${ay}" r="18" class="provider-marker"/><circle cx="${bx}" cy="${by}" r="18" class="customer-marker"/><text x="${ax + 24}" y="${ay - 20}" class="map-label">You</text><text x="${bx + 24}" y="${by - 20}" class="map-label">Customer</text></svg></div>`;
    if (steps) steps.innerHTML = points.route?.steps?.length ? points.route.steps.map((step) => `<li>${esc(step.name ? `${step.maneuver?.type || 'Continue'} on ${step.name}` : (step.maneuver?.type || 'Continue'))} — ${meters(Number(step.distance) || 0)}</li>`).join('') : '<li>Route steps are unavailable.</li>';
  }
  function load(position) {
    const data = new FormData();
    if (csrf) data.set('csrf_token', csrf);
    if (position?.coords) { data.set('latitude', position.coords.latitude); data.set('longitude', position.coords.longitude); }
    fetch(`/provider/bookings/${encodeURIComponent(reference)}/directions`, { method: 'POST', body: data, credentials: 'same-origin' })
      .then((response) => response.json().then((payload) => ({ response, payload })))
      .then(({ response, payload }) => {
        if (!response.ok) throw new Error(payload.error || 'Directions unavailable.');
        if (!valid(payload.provider) || !valid(payload.customer)) throw new Error('The booking location could not be displayed.');
        if (!payload.route?.geometry?.coordinates?.length) throw new Error("Route unavailable. We couldn't calculate a road route right now. Please try again.");
        points = payload; render(); status.textContent = position ? 'Using your current location.' : 'Using your saved provider location.';
        const hours = Math.floor(payload.route.duration_seconds / 3600), minutes = Math.round((payload.route.duration_seconds % 3600) / 60);
        summary.textContent = `Road distance: ${(payload.route.distance_meters / 1000).toFixed(1)} km · Estimated travel time: ${hours ? `${hours} hr ` : ''}${minutes} min`;
      }).catch((error) => { status.textContent = error.message; summary.textContent = ''; map.innerHTML = '<p class="map-fallback">This booking has no usable location data.</p>'; });
  }
  document.getElementById('center-provider')?.addEventListener('click', () => { if (points) render(); });
  document.getElementById('zoom-in')?.addEventListener('click', () => { zoom = Math.min(3, zoom + 1); if (points) render(); });
  document.getElementById('zoom-out')?.addEventListener('click', () => { zoom = Math.max(1, zoom - 1); if (points) render(); });
  if (navigator.geolocation) navigator.geolocation.getCurrentPosition(load, () => load(null), { timeout: 10000, maximumAge: 300000 }); else load(null);
})();
