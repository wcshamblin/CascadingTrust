from fastapi import APIRouter, HTTPException, status, Response, Cookie
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import jwt

# Handle imports whether running from backend/ or project root
try:
    from database import get_db_connection, get_site_id_for_node
    from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS, COOKIE_SECURE, COOKIE_SAMESITE
except ModuleNotFoundError:
    from backend.database import get_db_connection, get_site_id_for_node
    from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS, COOKIE_SECURE, COOKIE_SAMESITE


router = APIRouter(prefix="/api", tags=["jwt"])


class GenerateJWTRequest(BaseModel):
    node_id: int


class GenerateJWTResponse(BaseModel):
    token: str
    expires_at: str


class ValidateJWTRequest(BaseModel):
    token: str


class ValidateJWTForSiteRequest(BaseModel):
    token: str
    site_id: int


class ValidateJWTResponse(BaseModel):
    valid: bool
    node_id: Optional[int] = None
    site_id: Optional[int] = None


@router.post("/generate-jwt", response_model=GenerateJWTResponse)
async def generate_jwt(request: GenerateJWTRequest, response: Response):
    """
    Generate a JWT token for a given node_id.
    
    This endpoint:
    1. Validates that the node exists
    2. Finds the site_id for site-scoped token
    3. Creates a JWT token that expires in 7 days
    4. Stores the token in the database with site_id
    5. Sets the token as a cookie
    6. Returns the token and expiration time
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
        
        # Get the site_id for site-scoped token
        site_id = await get_site_id_for_node(db, request.node_id)
        if not site_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not determine site for this node"
            )
        
        # Generate expiration time (7 days from now)
        expires_at = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
        
        # Create JWT payload with site_id for site-scoped validation
        payload = {
            "node_id": request.node_id,
            "site_id": site_id,
            "exp": expires_at,
            "iat": datetime.utcnow()
        }
        
        # Generate JWT token
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        # Store token in database with site_id
        await db.execute(
            """
            INSERT INTO jwt_tokens (token, node_id, site_id, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, request.node_id, site_id, expires_at.isoformat())
        )
        await db.commit()
        
        # Set token as HTTP-only cookie for security
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=COOKIE_SECURE,  # True in production (HTTPS only)
            samesite=COOKIE_SAMESITE,
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
    Validate a JWT token (basic validation without site scope).
    
    WARNING: This endpoint validates ANY token regardless of site.
    For site-scoped validation, use /api/validate-jwt-for-site instead.
    
    This endpoint:
    1. Decodes the JWT token
    2. Checks if the token exists in the database and hasn't expired
    3. Returns 200 OK with node_id and site_id if valid, or 401 Unauthorized if invalid
    """
    db = await get_db_connection()
    
    try:
        # First, check if token exists in database
        cursor = await db.execute(
            """
            SELECT node_id, site_id, expires_at 
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
            site_id = payload.get("site_id")
            
            if not node_id or node_id != token_record['node_id']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            return ValidateJWTResponse(
                valid=True,
                node_id=node_id,
                site_id=site_id or token_record['site_id']
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


@router.post("/validate-jwt-for-site", response_model=ValidateJWTResponse)
async def validate_jwt_for_site_endpoint(request: ValidateJWTForSiteRequest):
    """
    Validate a JWT token for a specific site (site-scoped validation).
    
    This is the RECOMMENDED endpoint for external sites to validate tokens.
    It ensures the token was issued for the requesting site, preventing
    cross-site token reuse.
    
    This endpoint:
    1. Decodes the JWT token
    2. Checks if the token exists in the database
    3. Verifies the token was issued for the specified site_id
    4. Returns 200 OK if valid for that site, or 401 Unauthorized if invalid
    """
    db = await get_db_connection()
    
    try:
        # First, check if token exists in database
        cursor = await db.execute(
            """
            SELECT node_id, site_id, expires_at 
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
        
        # Check if token is for the correct site
        token_site_id = token_record['site_id']
        if token_site_id != request.site_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is not valid for this site"
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
            jwt_site_id = payload.get("site_id")
            
            if not node_id or node_id != token_record['node_id']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            # Double-check site_id from JWT payload if present
            if jwt_site_id and jwt_site_id != request.site_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token site mismatch"
                )
            
            return ValidateJWTResponse(
                valid=True,
                node_id=node_id,
                site_id=token_site_id
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token signature has expired"
            )
        except jwt.InvalidTokenError:
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


class TreeNode(BaseModel):
    """A node in the tree structure for display (no sensitive data)."""
    id: int
    node_type: str
    is_current: bool = False
    children: list["TreeNode"] = []


class AuthRedirectResponse(BaseModel):
    valid: bool
    redirect_url: Optional[str] = None
    token: Optional[str] = None
    site_id: Optional[int] = None
    password: Optional[str] = None
    trees: list[TreeNode] = []


async def get_site_redirect_url_for_node(db, node_id: int) -> tuple[str, Optional[int]]:
    """
    Traverse up the tree from any node to find the site's redirect_url and site_id.
    Returns (redirect_url, site_id).
    """
    current_id = node_id
    
    while current_id is not None:
        cursor = await db.execute(
            """
            SELECT id, node_type, parent_id, redirect_url
            FROM nodes
            WHERE id = ?
            """,
            (current_id,)
        )
        node = await cursor.fetchone()
        
        if not node:
            break
            
        if node['node_type'] == 'site':
            redirect_url = node['redirect_url'] if node['redirect_url'] else "/"
            return (redirect_url, node['id'])
            
        current_id = node['parent_id']
    
    return ("/", None)


async def get_password_for_node(db, node_id: int) -> Optional[str]:
    """
    Get the password value if the node is a password node.
    """
    cursor = await db.execute(
        """
        SELECT value, node_type FROM nodes WHERE id = ?
        """,
        (node_id,)
    )
    node = await cursor.fetchone()
    
    if node and node['node_type'] == 'password':
        return node['value']
    return None


async def build_all_trees(db, current_node_id: int) -> list[TreeNode]:
    """
    Build ALL trees in the system (all site nodes and their descendants).
    Hierarchy: site -> password -> invite
    Only includes node type and structure, not actual values.
    """
    # Get all root site nodes
    cursor = await db.execute(
        "SELECT id FROM nodes WHERE node_type = 'site' ORDER BY id"
    )
    root_rows = await cursor.fetchall()
    
    # Build tree recursively
    async def build_subtree(node_id: int) -> Optional[TreeNode]:
        cursor = await db.execute(
            "SELECT id, node_type FROM nodes WHERE id = ?",
            (node_id,)
        )
        node = await cursor.fetchone()
        
        if not node:
            return None
        
        # Get children
        cursor = await db.execute(
            "SELECT id FROM nodes WHERE parent_id = ? ORDER BY id",
            (node_id,)
        )
        child_rows = await cursor.fetchall()
        
        children = []
        for child_row in child_rows:
            child_tree = await build_subtree(child_row['id'])
            if child_tree:
                children.append(child_tree)
        
        return TreeNode(
            id=node['id'],
            node_type=node['node_type'],
            is_current=(node['id'] == current_node_id),
            children=children
        )
    
    trees = []
    for root_row in root_rows:
        tree = await build_subtree(root_row['id'])
        if tree:
            trees.append(tree)
    
    return trees


@router.get("/auth-redirect", response_model=AuthRedirectResponse)
async def check_auth_redirect(
    auth_token: Optional[str] = Cookie(None),
    for_site_id: Optional[int] = None
):
    """
    Check if user has valid auth and return redirect URL if so.
    
    This endpoint is used to check if a user visiting an invite page
    already has valid authentication. If they do, it returns the
    redirect URL for their authenticated site.
    
    IMPORTANT: If for_site_id is provided, this endpoint will ONLY return
    valid=True if the user's token is for that specific site. This prevents
    cross-site authentication bypass.
    
    Args:
        auth_token: JWT token from cookie
        for_site_id: Optional site ID to validate token against
    
    Returns valid=False if no valid auth, so frontend can proceed with invite.
    """
    if not auth_token:
        return AuthRedirectResponse(valid=False)
    
    db = await get_db_connection()
    
    try:
        # Check if token exists in database
        cursor = await db.execute(
            """
            SELECT node_id, site_id, expires_at 
            FROM jwt_tokens 
            WHERE token = ?
            """,
            (auth_token,)
        )
        token_record = await cursor.fetchone()
        
        if not token_record:
            return AuthRedirectResponse(valid=False)
        
        # If for_site_id is provided, check that the token is for that site
        token_site_id = token_record['site_id']
        if for_site_id is not None and token_site_id != for_site_id:
            # Token is valid but for a different site - don't auto-redirect
            return AuthRedirectResponse(valid=False)
        
        # Check if token has expired
        expires_at = datetime.fromisoformat(token_record['expires_at'])
        if datetime.utcnow() > expires_at:
            # Clean up expired token
            await db.execute(
                "DELETE FROM jwt_tokens WHERE token = ?",
                (auth_token,)
            )
            await db.commit()
            return AuthRedirectResponse(valid=False)
        
        # Verify JWT signature
        try:
            payload = jwt.decode(auth_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            node_id = payload.get("node_id")
            jwt_site_id = payload.get("site_id")
            
            if not node_id or node_id != token_record['node_id']:
                return AuthRedirectResponse(valid=False)
            
            # Double-check site_id from JWT if for_site_id is provided
            if for_site_id is not None and jwt_site_id and jwt_site_id != for_site_id:
                return AuthRedirectResponse(valid=False)
            
            # Get the redirect URL for this node's site
            redirect_url, site_id = await get_site_redirect_url_for_node(db, node_id)
            
            # Get password if the node is a password node
            password = await get_password_for_node(db, node_id)
            
            # Build tree data for visualization
            trees = await build_all_trees(db, node_id)
            
            return AuthRedirectResponse(
                valid=True,
                redirect_url=redirect_url,
                token=auth_token,
                site_id=site_id or token_site_id,
                password=password,
                trees=trees
            )
            
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return AuthRedirectResponse(valid=False)
        
    finally:
        await db.close()

