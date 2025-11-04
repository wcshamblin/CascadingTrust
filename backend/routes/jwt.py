from fastapi import APIRouter, HTTPException, status, Response, Cookie
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import jwt

# Handle imports whether running from backend/ or project root
try:
    from database import get_db_connection
    from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS
except ModuleNotFoundError:
    from backend.database import get_db_connection
    from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS


router = APIRouter(prefix="/api", tags=["jwt"])


class GenerateJWTRequest(BaseModel):
    node_id: int


class GenerateJWTResponse(BaseModel):
    token: str
    expires_at: str


class ValidateJWTRequest(BaseModel):
    token: str


class ValidateJWTResponse(BaseModel):
    valid: bool
    node_id: Optional[int] = None


@router.post("/generate-jwt", response_model=GenerateJWTResponse)
async def generate_jwt(request: GenerateJWTRequest, response: Response):
    """
    Generate a JWT token for a given node_id.
    
    This endpoint:
    1. Validates that the node exists
    2. Creates a JWT token that expires in 7 days
    3. Stores the token in the database
    4. Sets the token as a cookie
    5. Returns the token and expiration time
    """
    db = await get_db_connection()
    
    try:
        # Verify that the node exists
        cursor = await db.execute(
            "SELECT id FROM nodes WHERE id = ?",
            (request.node_id,)
        )
        node = await cursor.fetchone()
        
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Generate expiration time (7 days from now)
        expires_at = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
        
        # Create JWT payload
        payload = {
            "node_id": request.node_id,
            "exp": expires_at,
            "iat": datetime.utcnow()
        }
        
        # Generate JWT token
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        # Store token in database
        await db.execute(
            """
            INSERT INTO jwt_tokens (token, node_id, expires_at)
            VALUES (?, ?, ?)
            """,
            (token, request.node_id, expires_at.isoformat())
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
        
        return GenerateJWTResponse(
            token=token,
            expires_at=expires_at.isoformat()
        )
        
    finally:
        await db.close()


@router.post("/validate-jwt", response_model=ValidateJWTResponse)
async def validate_jwt_endpoint(request: ValidateJWTRequest):
    """
    Validate a JWT token.
    
    This endpoint:
    1. Decodes the JWT token
    2. Checks if the token exists in the database and hasn't expired
    3. Returns 200 OK if valid, or 401 Unauthorized if invalid
    """
    db = await get_db_connection()
    
    try:
        # First, check if token exists in database
        cursor = await db.execute(
            """
            SELECT node_id, expires_at 
            FROM jwt_tokens 
            WHERE token = ?
            """,
            (request.token,)
        )
        token_record = await cursor.fetchone()
        
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Check if token has expired in database
        expires_at = datetime.fromisoformat(token_record['expires_at'])
        if datetime.utcnow() > expires_at:
            # Clean up expired token
            await db.execute(
                "DELETE FROM jwt_tokens WHERE token = ?",
                (request.token,)
            )
            await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        
        # Verify JWT signature and decode
        try:
            payload = jwt.decode(request.token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            node_id = payload.get("node_id")
            
            if not node_id or node_id != token_record['node_id']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            return ValidateJWTResponse(
                valid=True,
                node_id=node_id
            )
            
        except jwt.ExpiredSignatureError:
            # Token signature has expired
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token signature has expired"
            )
        except jwt.InvalidTokenError:
            # Token is invalid
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
    finally:
        await db.close()


@router.get("/validate-jwt-cookie")
async def validate_jwt_cookie(auth_token: Optional[str] = Cookie(None)):
    """
    Validate a JWT token from a cookie.
    
    This is a convenience endpoint that reads the JWT from the cookie
    and validates it, returning 200 OK if valid or 401 Unauthorized if invalid.
    """
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token found"
        )
    
    # Use the validate_jwt_endpoint function
    request = ValidateJWTRequest(token=auth_token)
    return await validate_jwt_endpoint(request)

