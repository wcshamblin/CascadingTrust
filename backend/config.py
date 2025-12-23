"""
Configuration file for CascadingTrust backend.
Stores shared constants and secrets.
"""
import os
import sys
from pathlib import Path

# Load .env file if it exists
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# =============================================================================
# Environment Detection
# =============================================================================
PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"

# =============================================================================
# JWT Configuration
# =============================================================================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = int(os.getenv("JWT_EXPIRATION_DAYS", "7"))

# Validate JWT secret in production
if PRODUCTION and not JWT_SECRET_KEY:
    print("ERROR: JWT_SECRET_KEY environment variable must be set in production!", file=sys.stderr)
    print("Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(64))\"", file=sys.stderr)
    sys.exit(1)

# Use a development secret only in non-production mode
if not JWT_SECRET_KEY:
    JWT_SECRET_KEY = "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"
    print("WARNING: Using development JWT secret. Set JWT_SECRET_KEY for production.", file=sys.stderr)

# =============================================================================
# CORS Configuration
# =============================================================================
# Comma-separated list of allowed domains (without protocol)
ALLOWED_DOMAINS = os.getenv("ALLOWED_DOMAINS", "")
ALLOWED_DOMAINS_LIST = [d.strip() for d in ALLOWED_DOMAINS.split(",") if d.strip()]

# =============================================================================
# Cookie Configuration
# =============================================================================
# In production, cookies should be secure (HTTPS only)
COOKIE_SECURE = PRODUCTION
COOKIE_SAMESITE = "lax"

# =============================================================================
# Application URLs
# =============================================================================
BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")

