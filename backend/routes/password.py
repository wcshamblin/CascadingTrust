from fastapi import APIRouter, HTTPException, status, Response
from pydantic import BaseModel
from typing import List
import asyncio
from datetime import datetime, timedelta
import jwt

# Handle imports whether running from backend/ or project root
try:
    from database import get_db_connection, get_site_id_for_node
    from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS, COOKIE_SECURE, COOKIE_SAMESITE
except ModuleNotFoundError:
    from backend.database import get_db_connection, get_site_id_for_node
    from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS, COOKIE_SECURE, COOKIE_SAMESITE


router = APIRouter(prefix="/api", tags=["password"])


class TreeNode(BaseModel):
    """A node in the tree structure for display (no sensitive data)."""
    id: int
    node_type: str
    is_current: bool = False
    children: List["TreeNode"] = []


class PasswordRequest(BaseModel):
    password: str


class PasswordResponse(BaseModel):
    password: str  # Echo back for display
    redirect_url: str
    token: str
    trees: List[TreeNode]


async def get_site_redirect_url(db, password_node_id: int) -> str:
    """
    Get the redirect_url from the parent site of a password node.
    """
    cursor = await db.execute(
        """
        SELECT parent_id FROM nodes WHERE id = ?
        """,
        (password_node_id,)
    )
    password_node = await cursor.fetchone()
    
    if not password_node or not password_node['parent_id']:
        return "/"  # Default fallback
    
    site_id = password_node['parent_id']
    cursor = await db.execute(
        """
        SELECT redirect_url FROM nodes WHERE id = ? AND node_type = 'site'
        """,
        (site_id,)
    )
    site_node = await cursor.fetchone()
    
    return site_node['redirect_url'] if site_node and site_node['redirect_url'] else "/"


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


@router.post("/validate-password", response_model=PasswordResponse)
async def validate_password(request: PasswordRequest, response: Response):
    """
    Validate a password against the database.

    This endpoint:
    1. Takes 1.5 seconds to respond (security feature to prevent rapid guessing)
    2. Checks if the password exists in the database as an active password node
    3. Generates a JWT token for the user
    4. Returns the redirect URL from the parent site and token if valid, or 403 Forbidden if invalid
    """
    # Start 1.5-second delay timer as specified in requirements
    await asyncio.sleep(1.5)

    # Connect to database
    db = await get_db_connection()

    try:
        # Query for password node
        cursor = await db.execute(
            """
            SELECT id, value, is_active, expires_at, uses, max_uses, parent_id
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

        # Check if password has reached max uses
        if node['max_uses'] is not None and node['uses'] >= node['max_uses']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password has reached maximum uses"
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

        # Get redirect URL from parent site
        redirect_url = await get_site_redirect_url(db, node_id)
        
        # Build tree data for visualization
        trees = await build_all_trees(db, node_id)
        
        # Get site_id for site-scoped token
        site_id = await get_site_id_for_node(db, node_id)
        if not site_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not determine site for this password"
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
            max_age=JWT_EXPIRATION_DAYS * 24 * 60 * 60,  # 7 days in seconds
        )

        # Password is valid, return success with redirect URL from site, token, and tree
        return PasswordResponse(
            password=request.password,
            redirect_url=redirect_url,
            token=token,
            trees=trees
        )

    finally:
        await db.close()
