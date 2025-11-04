from fastapi import APIRouter, HTTPException, status, Response
from pydantic import BaseModel
import asyncio
from datetime import datetime, timedelta
import jwt

# Handle imports whether running from backend/ or project root
try:
    from database import get_db_connection
    from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS
except ModuleNotFoundError:
    from backend.database import get_db_connection
    from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS


router = APIRouter(prefix="/api", tags=["password"])


class PasswordRequest(BaseModel):
    password: str


class PasswordResponse(BaseModel):
    redirect_url: str
    token: str


@router.post("/validate-password", response_model=PasswordResponse)
async def validate_password(request: PasswordRequest, response: Response):
    """
    Validate a password against the database.

    This endpoint:
    1. Takes 1.5 seconds to respond (security feature to prevent rapid guessing)
    2. Checks if the password exists in the database as an active password node
    3. Generates a JWT token for the user
    4. Returns a redirect URL and token if valid, or 403 Forbidden if invalid
    """
    # Start 1.5-second delay timer as specified in requirements
    await asyncio.sleep(1.5)

    # Connect to database
    db = await get_db_connection()

    try:
        # Query for password node
        cursor = await db.execute(
            """
            SELECT id, value, is_active, expires_at, redirect_url
            FROM nodes
            WHERE node_type = 'password' AND value = ?
            """,
            (request.password,)
        )

        node = await cursor.fetchone()

        if not node:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid password"
            )

        # Check if node is active
        if not node['is_active']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password is not active"
            )

        # Check if password has expired
        if node['expires_at']:
            expires_at = datetime.fromisoformat(node['expires_at'])
            if datetime.now() > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Password has expired"
                )

        # Generate JWT token
        node_id = node['id']
        expires_at = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
        
        payload = {
            "node_id": node_id,
            "exp": expires_at,
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        # Store token in database
        await db.execute(
            """
            INSERT INTO jwt_tokens (token, node_id, expires_at)
            VALUES (?, ?, ?)
            """,
            (token, node_id, expires_at.isoformat())
        )
        await db.commit()
        
        # Set token as HTTP-only cookie for security
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=JWT_EXPIRATION_DAYS * 24 * 60 * 60,  # 7 days in seconds
        )

        # Password is valid, return success with redirect URL and token
        return PasswordResponse(redirect_url=node['redirect_url'], token=token)

    finally:
        await db.close()
