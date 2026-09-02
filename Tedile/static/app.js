async function loadServices() {
  const select = document.getElementById('search-service');
  if (!select) return;

  const response = await fetch('/api/services');
  const payload = await response.json();

  select.replaceChildren(new Option('All services', ''));
  payload.data.forEach(service => {
    select.appendChild(new Option(service.name, service.slug));
  });
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

  container.replaceChildren(...providers.map(provider => {
    const card = document.createElement('div');
    card.className = 'provider-card';

    const name = document.createElement('h3');
    name.textContent = provider.name;

    const location = document.createElement('p');
    location.textContent = `${provider.city || ''}${provider.state ? ', ' + provider.state : ''}`;

    const details = document.createElement('p');
    details.textContent = `Rating: ${provider.rating ?? 'N/A'} · Rate: ${provider.hourly_rate ?? 'N/A'}`;

    const verification = document.createElement('span');
    verification.className = `badge${provider.verified ? ' verified' : ''}`;
    verification.textContent = provider.verified ? 'Verified' : 'Unverified';

    card.append(name, location, details, verification);
    return card;
  }));
}

document.addEventListener('DOMContentLoaded', () => {
  loadServices();
  document.getElementById('search-btn')?.addEventListener('click', searchProviders);
  if (document.getElementById('provider-results')) {
    searchProviders();
  }

  document.querySelectorAll('.availability-form').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const message = form.querySelector('[data-availability-message]');
      const selected = form.elements.availability.value;
      const label = selected.charAt(0).toUpperCase() + selected.slice(1);
      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: new URLSearchParams(new FormData(form)),
          credentials: 'same-origin',
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || 'Unable to update availability.');
        message.className = 'success-banner';
        message.textContent = `Availability updated to ${label}.`;
        form.closest('.booking-grid').parentElement.querySelector('.status-pill').textContent = selected;
      } catch (error) {
        message.className = 'error-banner';
        message.textContent = error.message || 'Unable to update availability.';
      }
    });
  });

  document.querySelectorAll('.booking-status-form').forEach(form => {
    form.addEventListener('submit', event => {
      if (form.elements.status.value === 'cancelled' &&
          !window.confirm('Are you sure you want to cancel this booking?')) {
        event.preventDefault();
      }
    });
  });

});
