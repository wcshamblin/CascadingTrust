from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Handle imports whether running from backend/ or project root
try:
    from database import get_db_connection
except ModuleNotFoundError:
    from backend.database import get_db_connection

# Localhost addresses (IPv4 and IPv6)
LOCALHOST_ADDRESSES = {"127.0.0.1", "::1"}


async def require_localhost(request: Request):
    """
    Dependency that ensures requests only come from localhost.
    
    Security notes:
    - Checks request.client.host which is the actual TCP connection source
    - Does NOT trust X-Forwarded-For or similar headers (easily spoofed)
    - Blocks all non-localhost access with 403 Forbidden
    """
    client_host = request.client.host if request.client else None
    
    if client_host not in LOCALHOST_ADDRESSES:
        raise HTTPException(
            status_code=403,
            detail="Admin access restricted to localhost only"
        )


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_localhost)]
)


class NodeResponse(BaseModel):
    """Response model for a node."""
    id: int
    node_type: str
    value: str
    redirect_url: Optional[str]
    parent_id: Optional[int]
    uses: int
    max_uses: Optional[int]
    is_active: bool
    expires_at: Optional[str]
    created_at: str
    updated_at: str


class CreateNodeRequest(BaseModel):
    """Request model for creating a new node."""
    node_type: str  # 'site', 'password', or 'invite'
    value: str
    redirect_url: Optional[str] = None  # Only required for site nodes
    parent_id: Optional[int] = None
    max_uses: Optional[int] = None
    expires_at: Optional[str] = None


class UpdateNodeRequest(BaseModel):
    """Request model for updating a node."""
    redirect_url: Optional[str] = None
    parent_id: Optional[int] = None
    max_uses: Optional[int] = None
    is_active: Optional[bool] = None
    expires_at: Optional[str] = None


@router.get("/nodes", response_model=List[NodeResponse])
async def list_nodes():
    """
    List all nodes (passwords and invites) in the database.
    Returns nodes sorted by ID (ascending) for hierarchical display.
    """
    db = await get_db_connection()
    try:
        cursor = await db.execute("""
            SELECT 
                id, node_type, value, redirect_url, parent_id, uses, max_uses,
                is_active, expires_at, created_at, updated_at
            FROM nodes
            ORDER BY id ASC
        """)
        rows = await cursor.fetchall()
        
        nodes = []
        for row in rows:
            nodes.append(NodeResponse(
                id=row[0],
                node_type=row[1],
                value=row[2],
                redirect_url=row[3],
                parent_id=row[4],
                uses=row[5],
                max_uses=row[6],
                is_active=bool(row[7]),
                expires_at=row[8],
                created_at=row[9],
                updated_at=row[10]
            ))
        
        return nodes
    finally:
        await db.close()


@router.post("/nodes", response_model=NodeResponse)
async def create_node(request: CreateNodeRequest):
    """
    Create a new node (site, password, or invite).
    
    Hierarchy: site -> password -> invite
    
    Validations:
    - node_type must be 'site', 'password', or 'invite'
    - sites: cannot have a parent_id (root nodes), must have redirect_url
    - passwords: must have a parent_id pointing to a site
    - invites: must have a parent_id pointing to a password
    """
    # Validate node_type
    if request.node_type not in ['site', 'password', 'invite']:
        raise HTTPException(status_code=400, detail="node_type must be 'site', 'password', or 'invite'")
    
    # Validate site nodes
    if request.node_type == 'site':
        if request.parent_id is not None:
            raise HTTPException(status_code=400, detail="Sites cannot have a parent_id (they are root nodes)")
        if not request.redirect_url:
            raise HTTPException(status_code=400, detail="Sites must have a redirect_url")
    
    # Validate password nodes
    if request.node_type == 'password':
        if request.parent_id is None:
            raise HTTPException(status_code=400, detail="Passwords must have a parent_id (pointing to a site)")
    
    # Validate invite nodes
    if request.node_type == 'invite':
        if request.parent_id is None:
            raise HTTPException(status_code=400, detail="Invites must have a parent_id (pointing to a password or another invite)")
    
    db = await get_db_connection()
    try:
        # If parent_id is provided, verify it exists and has the correct type
        if request.parent_id is not None:
            cursor = await db.execute("SELECT id, node_type FROM nodes WHERE id = ?", (request.parent_id,))
            parent = await cursor.fetchone()
            if parent is None:
                raise HTTPException(status_code=404, detail=f"Parent node {request.parent_id} not found")
            
            parent_type = parent[1]
            # Validate parent type matches expected hierarchy
            if request.node_type == 'password' and parent_type != 'site':
                raise HTTPException(status_code=400, detail="Passwords must have a site as parent")
            if request.node_type == 'invite' and parent_type not in ('password', 'invite'):
                raise HTTPException(status_code=400, detail="Invites must have a password or another invite as parent")
        
        # Insert the new node
        cursor = await db.execute("""
            INSERT INTO nodes (
                node_type, value, redirect_url, parent_id, max_uses, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request.node_type,
            request.value,
            request.redirect_url,
            request.parent_id,
            request.max_uses,
            request.expires_at
        ))
        
        await db.commit()
        node_id = cursor.lastrowid
        
        # Fetch the created node
        cursor = await db.execute("""
            SELECT 
                id, node_type, value, redirect_url, parent_id, uses, max_uses,
                is_active, expires_at, created_at, updated_at
            FROM nodes
            WHERE id = ?
        """, (node_id,))
        
        row = await cursor.fetchone()
        
        return NodeResponse(
            id=row[0],
            node_type=row[1],
            value=row[2],
            redirect_url=row[3],
            parent_id=row[4],
            uses=row[5],
            max_uses=row[6],
            is_active=bool(row[7]),
            expires_at=row[8],
            created_at=row[9],
            updated_at=row[10]
        )
    finally:
        await db.close()


@router.patch("/nodes/{node_id}", response_model=NodeResponse)
async def update_node(node_id: int, request: UpdateNodeRequest):
    """
    Update a node's properties.
    
    Can update:
    - redirect_url
    - parent_id (for invites only)
    - max_uses
    - is_active (for revoking/activating)
    - expires_at
    """
    db = await get_db_connection()
    try:
        # Check if node exists
        cursor = await db.execute("SELECT node_type FROM nodes WHERE id = ?", (node_id,))
        node = await cursor.fetchone()
        if node is None:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        
        node_type = node[0]
        
        # Build update query dynamically based on provided fields
        update_fields = []
        update_values = []
        
        if request.redirect_url is not None:
            update_fields.append("redirect_url = ?")
            update_values.append(request.redirect_url)
        
        if request.parent_id is not None:
            # Sites cannot have a parent
            if node_type == 'site':
                raise HTTPException(status_code=400, detail="Cannot set parent_id for sites")
            
            # Verify parent exists and has correct type
            cursor = await db.execute("SELECT id, node_type FROM nodes WHERE id = ?", (request.parent_id,))
            parent = await cursor.fetchone()
            if parent is None:
                raise HTTPException(status_code=404, detail=f"Parent node {request.parent_id} not found")
            
            parent_type = parent[1]
            # Validate parent type matches expected hierarchy
            if node_type == 'password' and parent_type != 'site':
                raise HTTPException(status_code=400, detail="Passwords must have a site as parent")
            if node_type == 'invite' and parent_type not in ('password', 'invite'):
                raise HTTPException(status_code=400, detail="Invites must have a password or another invite as parent")
            
            update_fields.append("parent_id = ?")
            update_values.append(request.parent_id)
        
        if request.max_uses is not None:
            update_fields.append("max_uses = ?")
            update_values.append(request.max_uses)
        
        # Track if we're deactivating the node
        deactivating = False
        if request.is_active is not None:
            update_fields.append("is_active = ?")
            update_values.append(request.is_active)
            if request.is_active is False:
                deactivating = True
        
        if request.expires_at is not None:
            update_fields.append("expires_at = ?")
            update_values.append(request.expires_at)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Always update the updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        # Execute update
        update_query = f"UPDATE nodes SET {', '.join(update_fields)} WHERE id = ?"
        update_values.append(node_id)
        
        await db.execute(update_query, tuple(update_values))
        
        # If deactivating, also delete all JWT tokens for this node
        if deactivating:
            await db.execute(
                "DELETE FROM jwt_tokens WHERE node_id = ?",
                (node_id,)
            )
        
        await db.commit()
        
        # Fetch the updated node
        cursor = await db.execute("""
            SELECT 
                id, node_type, value, redirect_url, parent_id, uses, max_uses,
                is_active, expires_at, created_at, updated_at
            FROM nodes
            WHERE id = ?
        """, (node_id,))
        
        row = await cursor.fetchone()
        
        return NodeResponse(
            id=row[0],
            node_type=row[1],
            value=row[2],
            redirect_url=row[3],
            parent_id=row[4],
            uses=row[5],
            max_uses=row[6],
            is_active=bool(row[7]),
            expires_at=row[8],
            created_at=row[9],
            updated_at=row[10]
        )
    finally:
        await db.close()


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: int):
    """
    Delete a node from the database.
    This will cascade delete all child nodes and their associated JWT tokens.
    """
    db = await get_db_connection()
    try:
        # Check if node exists
        cursor = await db.execute("SELECT id FROM nodes WHERE id = ?", (node_id,))
        node = await cursor.fetchone()
        if node is None:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        
        # First, delete all JWT tokens for this node and its descendants
        # This is done explicitly for safety, even though CASCADE should handle it
        await db.execute("""
            WITH RECURSIVE descendants AS (
                SELECT id FROM nodes WHERE id = ?
                UNION ALL
                SELECT n.id FROM nodes n
                INNER JOIN descendants d ON n.parent_id = d.id
            )
            DELETE FROM jwt_tokens 
            WHERE node_id IN (SELECT id FROM descendants)
        """, (node_id,))
        
        # Delete the node (will cascade to children)
        await db.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        await db.commit()
        
        return {"message": f"Node {node_id} deleted successfully"}
    finally:
        await db.close()


@router.post("/nodes/{node_id}/revoke")
async def revoke_node(node_id: int):
    """
    Revoke a node by setting is_active to False.
    This also cascades to disable all children (descendants) of the node
    and invalidates all associated JWT tokens.
    """
    db = await get_db_connection()
    try:
        # Check if node exists
        cursor = await db.execute("SELECT id FROM nodes WHERE id = ?", (node_id,))
        node = await cursor.fetchone()
        if node is None:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        
        # Revoke the node and all its descendants using a recursive CTE
        await db.execute("""
            WITH RECURSIVE descendants AS (
                -- Base case: the node itself
                SELECT id FROM nodes WHERE id = ?
                UNION ALL
                -- Recursive case: all children of nodes already in the result
                SELECT n.id FROM nodes n
                INNER JOIN descendants d ON n.parent_id = d.id
            )
            UPDATE nodes 
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP 
            WHERE id IN (SELECT id FROM descendants)
        """, (node_id,))
        
        # Delete all JWT tokens for this node and its descendants
        await db.execute("""
            WITH RECURSIVE descendants AS (
                SELECT id FROM nodes WHERE id = ?
                UNION ALL
                SELECT n.id FROM nodes n
                INNER JOIN descendants d ON n.parent_id = d.id
            )
            DELETE FROM jwt_tokens 
            WHERE node_id IN (SELECT id FROM descendants)
        """, (node_id,))
        await db.commit()
        
        # Fetch the updated node
        cursor = await db.execute("""
            SELECT 
                id, node_type, value, redirect_url, parent_id, uses, max_uses,
                is_active, expires_at, created_at, updated_at
            FROM nodes
            WHERE id = ?
        """, (node_id,))
        
        row = await cursor.fetchone()
        
        return NodeResponse(
            id=row[0],
            node_type=row[1],
            value=row[2],
            redirect_url=row[3],
            parent_id=row[4],
            uses=row[5],
            max_uses=row[6],
            is_active=bool(row[7]),
            expires_at=row[8],
            created_at=row[9],
            updated_at=row[10]
        )
    finally:
        await db.close()

