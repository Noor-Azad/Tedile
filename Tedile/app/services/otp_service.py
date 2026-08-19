import os
import logging
import hashlib
from flask import current_app

logger = logging.getLogger(__name__)


def deliver_otp(destination, otp):
    """Deliver an OTP without exposing it through the browser or session."""
    provider = current_app.config.get(
        "OTP_DELIVERY_PROVIDER", os.getenv("OTP_DELIVERY_PROVIDER", "unconfigured")
    )
    if provider == "console":
        if current_app.config.get("APP_ENV") not in {"development", "uat"}:
            raise RuntimeError("Console OTP delivery is only available in development/UAT.")
        identifier = hashlib.sha256(destination.encode()).hexdigest()[:12]
        current_app.logger.info(
            "UAT OTP generated for user %s: %s",
            identifier,
            otp,
        )
        return True
    if provider == "unconfigured":
        return False
    # Future providers (for example MSG91) should be implemented here without
    # changing the authentication or OTP verification flow.
    return False
