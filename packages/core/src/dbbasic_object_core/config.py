"""
Object Primitive Configuration

Security and features are controlled via environment variables.
For production, set OBJPRIM_MODE=production.

Environment Variables:
    OBJPRIM_MODE        - "development" (default) or "production"
    OBJPRIM_AUTH_USER   - Basic auth username (default: admin)
    OBJPRIM_AUTH_PASS   - Basic auth password (required in production)
    OBJPRIM_RATE_LIMIT  - Requests per minute per IP (default: 1000, 0=disabled)
    OBJPRIM_SECRET_KEY  - Secret for tokens/sessions (auto-generated if not set)
    OBJPRIM_AUTH_VERIFY_URL - Optional URL for external token verification

Usage:
    from dbbasic_object_core.config import config

    if config.auth_enabled:
        # check auth

    if config.is_production:
        # strict mode
"""
import os
import secrets
from dataclasses import dataclass


@dataclass
class Config:
    """Runtime configuration"""

    # Mode
    mode: str = "development"

    # Auth
    auth_user: str = "admin"
    auth_pass: str | None = None

    # Token auth verify URL (optional; external service to validate bearer tokens)
    auth_verify_url: str = ""

    # Rate limiting
    rate_limit: int = 1000  # per minute, 0 = disabled

    # Security
    secret_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.mode == "production"

    @property
    def is_development(self) -> bool:
        return self.mode == "development"

    @property
    def auth_enabled(self) -> bool:
        """Auth is enabled if password is set OR in production mode"""
        if self.is_production:
            if not self.auth_pass:
                raise RuntimeError(
                    "OBJPRIM_AUTH_PASS required in production mode. "
                    "Set it or use OBJPRIM_MODE=development"
                )
            return True
        return bool(self.auth_pass)

    @property
    def rate_limit_enabled(self) -> bool:
        return self.rate_limit > 0


def load_config() -> Config:
    """Load config from environment"""
    mode = os.environ.get("OBJPRIM_MODE", "development").lower()

    # Validate mode
    if mode not in ("development", "production"):
        raise ValueError(f"OBJPRIM_MODE must be 'development' or 'production', got: {mode}")

    # Generate secret if not provided
    secret = os.environ.get("OBJPRIM_SECRET_KEY") or secrets.token_hex(32)

    return Config(
        mode=mode,
        auth_user=os.environ.get("OBJPRIM_AUTH_USER", "admin"),
        auth_pass=os.environ.get("OBJPRIM_AUTH_PASS"),
        auth_verify_url=os.environ.get("OBJPRIM_AUTH_VERIFY_URL", ""),
        rate_limit=int(os.environ.get("OBJPRIM_RATE_LIMIT", "1000")),
        secret_key=secret,
    )


# Global config instance
config = load_config()


def print_config_status():
    """Print current config for debugging"""
    print(f"Object Primitive Configuration:")
    print(f"  Mode: {config.mode}")
    print(f"  Auth enabled: {config.auth_enabled if config.auth_pass or not config.is_production else 'REQUIRED'}")
    print(f"  Rate limit: {config.rate_limit}/min" if config.rate_limit_enabled else "  Rate limit: disabled")
    if config.is_development:
        print(f"  ⚠️  Development mode - security features relaxed")
    else:
        print(f"  🔒 Production mode - security enforced")
