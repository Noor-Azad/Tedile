async function loadServices() {
  const select = document.getElementById('search-service');
  if (!select) return;

  const response = await fetch('/api/services');
  const payload = await response.json();

  select.innerHTML = '<option value="">All services</option>' +
    payload.data.map(service => `<option value="${service.slug}">${service.name}</option>`).join('');
}

async function searchProviders() {
  const keyword = document.getElementById('search-keyword')?.value || '';
  const service = document.getElementById('search-service')?.value || '';

  const params = new URLSearchParams();
  if (keyword) params.append('keyword', keyword);
  if (service) params.append('service', service);
  params.append('sort', 'rating-high');

  const response = await fetch(`/api/search/providers?${params.toString()}`);
  const payload = await response.json();
  renderProviders(payload.data.providers);
}

function renderProviders(providers) {
  const container = document.getElementById('provider-results');
  if (!container) return;

  if (!providers.length) {
    container.innerHTML = '<p>No providers found.</p>';
    return;
  }

  container.innerHTML = providers.map(provider => `
    <div class="provider-card">
      <h3>${provider.name}</h3>
      <p>${provider.city || ''}${provider.state ? ', ' + provider.state : ''}</p>
      <p>Rating: ${provider.rating ?? 'N/A'} · Rate: ${provider.hourly_rate ?? 'N/A'}</p>
      <span class="badge ${provider.verified ? 'verified' : ''}">${provider.verified ? 'Verified' : 'Unverified'}</span>
    </div>
  `).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  loadServices();
  document.getElementById('search-btn')?.addEventListener('click', searchProviders);
  if (document.getElementById('provider-results')) {
    searchProviders();
  }
});
