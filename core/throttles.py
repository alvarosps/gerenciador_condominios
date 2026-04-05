from rest_framework.throttling import AnonRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """Strict rate limit for authentication endpoints."""

    scope = "auth"


class VerificationRateThrottle(AnonRateThrottle):
    """Rate limit for OTP/verification endpoints."""

    scope = "verification"
