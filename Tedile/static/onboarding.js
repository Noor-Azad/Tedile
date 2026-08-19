(function () {
  const token = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const status = document.getElementById("location-status");
  const send = async (url, body) => {
    const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": token }, body: JSON.stringify(body || {}) });
    if (!response.ok) throw new Error("location request failed");
    const payload = await response.json();
    window.location.assign(payload.next);
  };
  document.getElementById("allow-location")?.addEventListener("click", () => {
    if (!navigator.geolocation) { status.textContent = "Location is not available in this browser."; return; }
    status.textContent = "Requesting location permission…";
    navigator.geolocation.getCurrentPosition(position => send("/onboarding/location", { latitude: position.coords.latitude, longitude: position.coords.longitude }).catch(() => { status.textContent = "We could not save that location. You can continue without it."; }), () => { status.textContent = "Location permission was denied. You can continue without it."; });
  });
  document.getElementById("skip-location")?.addEventListener("click", () => send("/onboarding/location/skip").catch(() => { status.textContent = "You can continue without location."; }));
}());
