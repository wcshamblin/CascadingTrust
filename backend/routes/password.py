from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import asyncio
from datetime import datetime

# Handle imports whether running from backend/ or project root
try:
    from database import get_db_connection
except ModuleNotFoundError:
    from backend.database import get_db_connection


router = APIRouter(prefix="/api", tags=["password"])


class PasswordRequest(BaseModel):
    password: str


class PasswordResponse(BaseModel):
    redirect_url: str


@router.post("/validate-password", response_model=PasswordResponse)
async def validate_password(request: PasswordRequest):
    """
    Validate a password against the database.

    This endpoint:
    1. Takes 1.5 seconds to respond (security feature to prevent rapid guessing)
    2. Checks if the password exists in the database as an active password node
    3. Returns a redirect URL if valid, or 403 Forbidden if invalid
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

        # Password is valid, return success with redirect URL from database
        return PasswordResponse(redirect_url=node['redirect_url'])

    finally:
        await db.close()
