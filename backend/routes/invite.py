from fastapi import APIRouter, HTTPException, status, Response, Cookie, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
import secrets

# Handle imports whether running from backend/ or project root
try:
    from database import get_db_connection, get_site_id_for_node
    from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS, COOKIE_SECURE, COOKIE_SAMESITE, BASE_URL
except ModuleNotFoundError:
    from backend.database import get_db_connection, get_site_id_for_node
    from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS, COOKIE_SECURE, COOKIE_SAMESITE, BASE_URL


router = APIRouter(prefix="/api", tags=["invite"])


class TreeNode(BaseModel):
    """A node in the tree structure for display (no sensitive data)."""
    id: int
    node_type: str
    is_current: bool = False
    children: List["TreeNode"] = []


class InviteResponse(BaseModel):
    """Response when an invite is successfully validated."""
    password: str
    redirect_url: str
    token: str
    trees: List[TreeNode]  # All trees in the system (site -> password -> invite)


async def get_password_for_node(db, node_id: int) -> str:
    """
    Traverse up the tree from an invite to find the parent password value.
    """
    current_id = node_id
    
    while current_id is not None:
        cursor = await db.execute(
            """
            SELECT id, node_type, parent_id, value
            FROM nodes
            WHERE id = ?
            """,
            (current_id,)
        )
        node = await cursor.fetchone()
        
        if not node:
            break
            
        if node['node_type'] == 'password':
            return node['value']
            
        current_id = node['parent_id']
    
    return ""


async def get_site_redirect_url(db, node_id: int) -> str:
    """
    Traverse up the tree from an invite to find the site's redirect_url.
    Hierarchy: site -> password -> invite
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
            return node['redirect_url'] if node['redirect_url'] else "/"
            
        current_id = node['parent_id']
    
    return "/"


async def build_all_trees(db, current_node_id: int) -> List[TreeNode]:
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
    async def build_subtree(node_id: int) -> TreeNode:
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


@router.get("/invite/{code}", response_model=InviteResponse)
async def validate_invite(code: str, response: Response):
    """
    Validate an invite code and return the password, redirect URL, JWT token, and ancestry chain.

    This endpoint:
    1. Checks if the invite code exists in the database as an active invite node
    2. Validates expiration and max uses
    3. Increments the usage counter
    4. Generates a JWT token for the user
    5. Returns the password (from parent password node), redirect URL (from site), token, and tree if valid
    """
    db = await get_db_connection()

    try:
        # Query for invite node
        cursor = await db.execute(
            """
            SELECT id, value, is_active, expires_at, uses, max_uses, parent_id
            FROM nodes
            WHERE node_type = 'invite' AND value = ?
            """,
            (code,)
        )

        node = await cursor.fetchone()

        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invite code not found"
            )

        # Check if node is active
        if not node['is_active']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invite code is not active"
            )

        # Check if invite has expired
        if node['expires_at']:
            expires_at = datetime.fromisoformat(node['expires_at'])
            if datetime.now() > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invite code has expired"
                )

        # Check if invite has reached max uses
        if node['max_uses'] is not None and node['uses'] >= node['max_uses']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invite code has reached maximum uses"
            )

        # Increment the uses counter
        node_id = node['id']
        await db.execute(
            """
            UPDATE nodes 
            SET uses = uses + 1, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
            """,
            (node_id,)
        )
        await db.commit()

        # Get the password value and redirect URL from the hierarchy
        password_value = await get_password_for_node(db, node_id)
        redirect_url = await get_site_redirect_url(db, node_id)
        trees = await build_all_trees(db, node_id)
        
        # Get site_id for site-scoped token
        site_id = await get_site_id_for_node(db, node_id)
        if not site_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not determine site for this invite"
            )

        # Generate JWT token with site_id for site-scoped validation
        jwt_expires_at = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
        
        payload = {
            "node_id": node_id,
            "site_id": site_id,
            "exp": jwt_expires_at,
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        # Store token in database with site_id
        await db.execute(
            """
            INSERT INTO jwt_tokens (token, node_id, site_id, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, node_id, site_id, jwt_expires_at.isoformat())
        )
        await db.commit()
        
        # Set token as HTTP-only cookie for security
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=COOKIE_SECURE,  # True in production (HTTPS only)
            samesite=COOKIE_SAMESITE,
            max_age=JWT_EXPIRATION_DAYS * 24 * 60 * 60,
        )

        # Return the password, redirect URL from site, token, and all tree structures
        return InviteResponse(
            password=password_value,
            redirect_url=redirect_url,
            token=token,
            trees=trees
        )

    finally:
        await db.close()


class GenerateInviteRequest(BaseModel):
    """Request model for generating a new invite."""
    max_uses: Optional[int] = None  # Optional: limit how many times this invite can be used
    expires_in_days: Optional[int] = None  # Optional: how many days until the invite expires


class GenerateInviteResponse(BaseModel):
    """Response model for a generated invite."""
    invite_code: str
    invite_url: str
    node_id: int
    parent_node_id: int
    site_id: int
    expires_at: Optional[str] = None


def generate_invite_code(length: int = 12) -> str:
    """Generate a secure random invite code."""
    # Use URL-safe base64 characters for the code
    return secrets.token_urlsafe(length)


async def validate_token_and_get_info(
    db,
    token: str
) -> tuple[int, int]:
    """
    Validate a JWT token and return (node_id, site_id).
    Raises HTTPException if invalid.
    """
    # Check if token exists in database
    cursor = await db.execute(
        """
        SELECT node_id, site_id, expires_at 
        FROM jwt_tokens 
        WHERE token = ?
        """,
        (token,)
    )
    token_record = await cursor.fetchone()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Check if token has expired
    expires_at = datetime.fromisoformat(token_record['expires_at'])
    if datetime.utcnow() > expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    
    # Verify JWT signature
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        node_id = payload.get("node_id")
        site_id = payload.get("site_id")
        
        if not node_id or node_id != token_record['node_id']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return (node_id, site_id or token_record['site_id'])
        
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


@router.post("/generate-invite", response_model=GenerateInviteResponse)
async def generate_invite(
    request: GenerateInviteRequest = GenerateInviteRequest(),
    auth_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    """
    Generate a new invite code for the authenticated user.
    
    This endpoint:
    1. Validates the JWT token (from cookie or Authorization header)
    2. Ensures the token is valid for a specific site
    3. Creates a new invite node as a child of the node the user authenticated with
    4. Returns the invite code and URL
    
    The new invite becomes a child of the node used for authentication:
    - If user logged in with a password, invite is child of that password
    - If user logged in with an invite, invite is child of that invite
    
    Authentication:
    - Cookie: auth_token
    - Header: Authorization: Bearer <token>
    """
    # Get token from cookie or Authorization header
    token = None
    if auth_token:
        token = auth_token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided. Include auth_token cookie or Authorization header."
        )
    
    db = await get_db_connection()
    
    try:
        # Validate token and get node_id and site_id
        node_id, site_id = await validate_token_and_get_info(db, token)
        
        # Verify the parent node exists and is active
        cursor = await db.execute(
            """
            SELECT id, node_type, is_active, site_id
            FROM nodes n
            LEFT JOIN (
                SELECT id as site_id, node_type as site_type
                FROM nodes
                WHERE node_type = 'site'
            ) s ON 1=1
            WHERE n.id = ?
            """,
            (node_id,)
        )
        parent_node = await cursor.fetchone()
        
        if not parent_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent node not found"
            )
        
        # Verify the parent node is a password or invite (not a site)
        cursor = await db.execute(
            "SELECT node_type, is_active FROM nodes WHERE id = ?",
            (node_id,)
        )
        node_info = await cursor.fetchone()
        
        if not node_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        if node_info['node_type'] not in ('password', 'invite'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only generate invites from password or invite nodes"
            )
        
        if not node_info['is_active']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot generate invite from an inactive node"
            )
        
        # Generate a unique invite code
        invite_code = generate_invite_code()
        
        # Ensure the code is unique
        cursor = await db.execute(
            "SELECT id FROM nodes WHERE value = ? AND node_type = 'invite'",
            (invite_code,)
        )
        while await cursor.fetchone():
            invite_code = generate_invite_code()
            cursor = await db.execute(
                "SELECT id FROM nodes WHERE value = ? AND node_type = 'invite'",
                (invite_code,)
            )
        
        # Calculate expiration if specified
        expires_at = None
        if request.expires_in_days:
            expires_at = (datetime.utcnow() + timedelta(days=request.expires_in_days)).isoformat()
        
        # Create the new invite node as a child of the authenticated node
        cursor = await db.execute(
            """
            INSERT INTO nodes (
                node_type, value, parent_id, max_uses, expires_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                'invite',
                invite_code,
                node_id,  # Parent is the node used to authenticate
                request.max_uses,
                expires_at
            )
        )
        await db.commit()
        
        new_node_id = cursor.lastrowid
        
        # Build the invite URL
        # Uses BASE_URL from config (defaults to localhost in dev)
        invite_url = f"{BASE_URL}/invite/{invite_code}"
        
        return GenerateInviteResponse(
            invite_code=invite_code,
            invite_url=invite_url,
            node_id=new_node_id,
            parent_node_id=node_id,
            site_id=site_id,
            expires_at=expires_at
        )
    
    finally:
        await db.close()

