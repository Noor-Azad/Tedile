(function () {
  const token = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const status = document.getElementById("location-status");
  const allowButton = document.getElementById("allow-location");
  const send = async (url, body) => {
    const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": token }, body: JSON.stringify(body || {}) });
    if (!response.ok) throw new Error("location request failed");
    const payload = await response.json();
    window.location.assign(payload.next);
  };
  allowButton?.addEventListener("click", () => {
    if (!navigator.geolocation) { status.textContent = "Location is not available in this browser. Try again on a supported browser."; allowButton.textContent = "Try Again"; return; }
    status.textContent = "Requesting location permission…";
    allowButton.textContent = "Try Again";
    navigator.geolocation.getCurrentPosition(position => send("/onboarding/location", { latitude: position.coords.latitude, longitude: position.coords.longitude }).catch(() => { status.textContent = "We could not save that location. You can try again."; }), error => {
      const messages = { 1: "Location permission was denied. You can try again.", 2: "Your location is currently unavailable. You can try again.", 3: "Location request timed out. You can try again." };
      status.textContent = messages[error.code] || "We could not get your location. You can try again.";
    });
  });
}());
