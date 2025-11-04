"""
Configuration file for CascadingTrust backend.
Stores shared constants and secrets.
"""
import os

# JWT Configuration
# In production, this should be stored in environment variables and be a strong random secret
# For development, we use a fixed secret key so tokens persist across server restarts
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production-12345678901234567890")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7

