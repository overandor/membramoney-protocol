"""
Environment-based feature flags for Membra Money Protocol.
Allows gradual rollout of features without code changes.
"""

import os
from typing import Set


class FeatureFlags:
    """Feature flag configuration."""

    # Feature definitions
    CLAIM_IDEMPOTENCY = "claim_idempotency"
    STRUCTURED_LOGGING = "structured_logging"
    RATE_LIMITING = "rate_limiting"
    AUDIT_EVENTS = "audit_events"
    REDIS_CACHE = "redis_cache"
    METRICS = "metrics"
    SENTRY = "sentry"
    CIRCUIT_BREAKER = "circuit_breaker"

    # Default enabled features by environment
    DEFAULTS = {
        "devnet": {
            CLAIM_IDEMPOTENCY,
            STRUCTURED_LOGGING,
            RATE_LIMITING,
            AUDIT_EVENTS,
            METRICS,
        },
        "staging": {
            CLAIM_IDEMPOTENCY,
            STRUCTURED_LOGGING,
            RATE_LIMITING,
            AUDIT_EVENTS,
            REDIS_CACHE,
            METRICS,
            CIRCUIT_BREAKER,
        },
        "production": {
            CLAIM_IDEMPOTENCY,
            STRUCTURED_LOGGING,
            RATE_LIMITING,
            AUDIT_EVENTS,
            REDIS_CACHE,
            METRICS,
            SENTRY,
            CIRCUIT_BREAKER,
        },
    }

    def __init__(self, env: str = "devnet"):
        self.env = env
        self._enabled = self._load_flags()

    def _load_flags(self) -> Set[str]:
        """Load feature flags from environment and defaults."""
        # Start with defaults for this environment
        enabled = set(self.DEFAULTS.get(self.env, self.DEFAULTS["devnet"]))

        # Override with environment variables
        # Format: ENABLE_FEATURE_X=1 or DISABLE_FEATURE_Y=1
        for key, value in os.environ.items():
            if key.startswith("ENABLE_"):
                feature = key[7:].lower().replace("_", "")
                if value.lower() in ("1", "true", "yes"):
                    enabled.add(feature)
                elif value.lower() in ("0", "false", "no"):
                    enabled.discard(feature)

        return enabled

    def is_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return feature in self._enabled

    def enable(self, feature: str):
        """Enable a feature (for testing)."""
        self._enabled.add(feature)

    def disable(self, feature: str):
        """Disable a feature (for testing)."""
        self._enabled.discard(feature)

    def list_enabled(self) -> Set[str]:
        """List all enabled features."""
        return set(self._enabled)

    def to_dict(self) -> dict:
        """Export feature flags as a dictionary."""
        all_features = {
            self.CLAIM_IDEMPOTENCY,
            self.STRUCTURED_LOGGING,
            self.RATE_LIMITING,
            self.AUDIT_EVENTS,
            self.REDIS_CACHE,
            self.METRICS,
            self.SENTRY,
            self.CIRCUIT_BREAKER,
        }
        return {
            "environment": self.env,
            "enabled": list(self._enabled),
            "disabled": list(all_features - self._enabled),
        }


# Global instance (lazy-loaded)
_flags = None


def get_flags(env: str = None) -> FeatureFlags:
    """Get the global feature flags instance."""
    global _flags
    if _flags is None or (env is not None and _flags.env != env):
        from core.config import settings
        _flags = FeatureFlags(env or settings.env)
    return _flags
