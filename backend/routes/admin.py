from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Handle imports whether running from backend/ or project root
try:
    from database import get_db_connection
except ModuleNotFoundError:
    from backend.database import get_db_connection

router = APIRouter(prefix="/api/admin", tags=["admin"])


class NodeResponse(BaseModel):
    """Response model for a node."""
    id: int
    node_type: str
    value: str
    redirect_url: str
    parent_id: Optional[int]
    uses: int
    max_uses: Optional[int]
    is_active: bool
    expires_at: Optional[str]
    created_at: str
    updated_at: str


class CreateNodeRequest(BaseModel):
    """Request model for creating a new node."""
    node_type: str  # 'password' or 'invite'
    value: str
    redirect_url: str
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
    Returns nodes sorted by creation date (newest first).
    """
    db = await get_db_connection()
    try:
        cursor = await db.execute("""
            SELECT 
                id, node_type, value, redirect_url, parent_id, uses, max_uses,
                is_active, expires_at, created_at, updated_at
            FROM nodes
            ORDER BY created_at DESC
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
    Create a new node (password or invite).
    
    Validations:
    - node_type must be 'password' or 'invite'
    - invites must have a parent_id
    - passwords should not have a parent_id
    """
    # Validate node_type
    if request.node_type not in ['password', 'invite']:
        raise HTTPException(status_code=400, detail="node_type must be 'password' or 'invite'")
    
    # Validate parent_id for invites
    if request.node_type == 'invite' and request.parent_id is None:
        raise HTTPException(status_code=400, detail="Invites must have a parent_id")
    
    # Validate that passwords don't have parent_id (they are root nodes)
    if request.node_type == 'password' and request.parent_id is not None:
        raise HTTPException(status_code=400, detail="Passwords cannot have a parent_id (they are root nodes)")
    
    db = await get_db_connection()
    try:
        # If parent_id is provided, verify it exists
        if request.parent_id is not None:
            cursor = await db.execute("SELECT id FROM nodes WHERE id = ?", (request.parent_id,))
            parent = await cursor.fetchone()
            if parent is None:
                raise HTTPException(status_code=404, detail=f"Parent node {request.parent_id} not found")
        
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
            # Only allow updating parent_id for invites
            if node_type != 'invite':
                raise HTTPException(status_code=400, detail="Cannot set parent_id for passwords")
            
            # Verify parent exists
            cursor = await db.execute("SELECT id FROM nodes WHERE id = ?", (request.parent_id,))
            parent = await cursor.fetchone()
            if parent is None:
                raise HTTPException(status_code=404, detail=f"Parent node {request.parent_id} not found")
            
            update_fields.append("parent_id = ?")
            update_values.append(request.parent_id)
        
        if request.max_uses is not None:
            update_fields.append("max_uses = ?")
            update_values.append(request.max_uses)
        
        if request.is_active is not None:
            update_fields.append("is_active = ?")
            update_values.append(request.is_active)
        
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
    This will cascade delete all child nodes due to the foreign key constraint.
    """
    db = await get_db_connection()
    try:
        # Check if node exists
        cursor = await db.execute("SELECT id FROM nodes WHERE id = ?", (node_id,))
        node = await cursor.fetchone()
        if node is None:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        
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
    This is a convenience endpoint for deactivating a node.
    """
    db = await get_db_connection()
    try:
        # Check if node exists
        cursor = await db.execute("SELECT id FROM nodes WHERE id = ?", (node_id,))
        node = await cursor.fetchone()
        if node is None:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        
        # Revoke the node
        await db.execute("""
            UPDATE nodes 
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
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

