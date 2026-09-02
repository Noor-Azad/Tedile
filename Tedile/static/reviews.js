document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.review-form').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const status = document.createElement('p');
      status.className = 'form-status';
      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          credentials: 'same-origin',
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || 'Unable to submit review.');
        status.textContent = `Your rating: ${form.elements.rating.value}/5`;
        if (form.elements.comment.value.trim()) status.textContent += ` — ${form.elements.comment.value.trim()}`;
        form.replaceWith(status);
      } catch (error) {
        status.className = 'error-banner';
        status.textContent = error.message || 'Unable to submit review.';
        form.appendChild(status);
      }
    });
  });
});
