from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Handle imports whether running from backend/ or project root
try:
    from database import init_database
    from routes.password import router as password_router
    from routes.jwt import router as jwt_router
except ModuleNotFoundError:
    from backend.database import init_database
    from backend.routes.password import router as password_router
    from backend.routes.jwt import router as jwt_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_database()
    yield


app = FastAPI(lifespan=lifespan)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(password_router)
app.include_router(jwt_router)


@app.get("/")
async def root():
    return {"message": "CascadingTrust API"}
