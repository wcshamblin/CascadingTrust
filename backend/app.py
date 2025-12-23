import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Handle imports whether running from backend/ or project root
try:
    from database import init_database
    from config import PRODUCTION, ALLOWED_DOMAINS_LIST
    from routes.password import router as password_router
    from routes.jwt import router as jwt_router
    from routes.admin import router as admin_router
    from routes.invite import router as invite_router
except ModuleNotFoundError:
    from backend.database import init_database
    from backend.config import PRODUCTION, ALLOWED_DOMAINS_LIST
    from backend.routes.password import router as password_router
    from backend.routes.jwt import router as jwt_router
    from backend.routes.admin import router as admin_router
    from backend.routes.invite import router as invite_router


def build_cors_regex() -> str:
    """
    Build a regex pattern for allowed CORS origins.
    Always allows localhost for development.
    Adds configured domains for production.
    """
    # Always allow localhost (any port) for development
    patterns = [r"https?://localhost(:\d+)?"]
    
    # Add configured production domains
    for domain in ALLOWED_DOMAINS_LIST:
        # Escape dots in domain and allow both http and https
        escaped_domain = re.escape(domain)
        patterns.append(f"https?://{escaped_domain}")
    
    # Combine all patterns
    return f"^({'|'.join(patterns)})$"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_database()
    yield


app = FastAPI(lifespan=lifespan)

# Configure CORS for frontend
# - Always allows localhost for development
# - Adds domains from ALLOWED_DOMAINS env var for production
cors_regex = build_cors_regex()
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(password_router)
app.include_router(jwt_router)
app.include_router(admin_router)
app.include_router(invite_router)


@app.get("/")
async def root():
    return {"message": "CascadingTrust API"}


@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    Returns 200 OK if the service is running.
    
    For a more comprehensive check, you could add:
    - Database connectivity check
    - Memory/CPU usage
    - Dependency health checks
    """
    return {
        "status": "healthy",
        "service": "cascadingtrust-api",
        "production": PRODUCTION
    }
