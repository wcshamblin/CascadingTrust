#!/usr/bin/env python3
"""
Helper script to add passwords and invites to the database.

Usage:
    python add_node.py password <password_value> <redirect_url>
    python add_node.py invite <invite_code> <redirect_url> [--parent-id <id>] [--max-uses <number>]
"""

import asyncio
import sys
from database import get_db_connection, init_database


async def add_password(password: str, redirect_url: str):
    """Add a new password node to the database."""
    await init_database()
    db = await get_db_connection()
    
    try:
        await db.execute(
            """
            INSERT INTO nodes (node_type, value, redirect_url)
            VALUES ('password', ?, ?)
            """,
            (password, redirect_url)
        )
        await db.commit()
        
        # Get the ID of the inserted node
        cursor = await db.execute(
            "SELECT id FROM nodes WHERE value = ? AND node_type = 'password'",
            (password,)
        )
        row = await cursor.fetchone()
        
        print(f"✓ Password '{password}' added successfully!")
        print(f"  ID: {row['id']}")
        print(f"  Redirect URL: {redirect_url}")
        
    except Exception as e:
        print(f"✗ Error adding password: {e}")
    finally:
        await db.close()


async def add_invite(invite_code: str, redirect_url: str, parent_id: int = None, max_uses: int = None):
    """Add a new invite node to the database."""
    await init_database()
    db = await get_db_connection()
    
    try:
        if max_uses is not None:
            await db.execute(
                """
                INSERT INTO nodes (node_type, value, redirect_url, parent_id, max_uses)
                VALUES ('invite', ?, ?, ?, ?)
                """,
                (invite_code, redirect_url, parent_id, max_uses)
            )
        else:
            await db.execute(
                """
                INSERT INTO nodes (node_type, value, redirect_url, parent_id)
                VALUES ('invite', ?, ?, ?)
                """,
                (invite_code, redirect_url, parent_id)
            )
        
        await db.commit()
        
        # Get the ID of the inserted node
        cursor = await db.execute(
            "SELECT id FROM nodes WHERE value = ? AND node_type = 'invite'",
            (invite_code,)
        )
        row = await cursor.fetchone()
        
        print(f"✓ Invite '{invite_code}' added successfully!")
        print(f"  ID: {row['id']}")
        print(f"  Redirect URL: {redirect_url}")
        if parent_id:
            print(f"  Parent ID: {parent_id}")
        if max_uses:
            print(f"  Max uses: {max_uses}")
        
    except Exception as e:
        print(f"✗ Error adding invite: {e}")
    finally:
        await db.close()


async def list_nodes():
    """List all nodes in the database."""
    await init_database()
    db = await get_db_connection()
    
    try:
        cursor = await db.execute(
            """
            SELECT id, node_type, value, redirect_url, parent_id, uses, max_uses, is_active
            FROM nodes
            ORDER BY id
            """
        )
        rows = await cursor.fetchall()
        
        if not rows:
            print("No nodes found in database.")
            return
        
        print("\n┌────────────────────────────────────────────────────────────────────┐")
        print("│                       Database Nodes                               │")
        print("├────┬──────────┬──────────────┬────────────────────────────────────┤")
        print("│ ID │ Type     │ Value        │ Redirect URL                       │")
        print("├────┼──────────┼──────────────┼────────────────────────────────────┤")
        
        for row in rows:
            node_type = row['node_type'].ljust(8)
            value = (row['value'][:12] + '..') if len(row['value']) > 14 else row['value'].ljust(12)
            redirect_url = (row['redirect_url'][:30] + '..') if len(row['redirect_url']) > 32 else row['redirect_url'].ljust(32)
            print(f"│ {row['id']:2d} │ {node_type} │ {value} │ {redirect_url} │")
        
        print("└────┴──────────┴──────────────┴────────────────────────────────────┘\n")
        
    finally:
        await db.close()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python add_node.py password <password> <redirect_url>")
        print("  python add_node.py invite <invite_code> <redirect_url> [--parent-id <id>] [--max-uses <number>]")
        print("  python add_node.py list")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        asyncio.run(list_nodes())
    elif command == "password":
        if len(sys.argv) < 4:
            print("Error: password requires <password> and <redirect_url>")
            sys.exit(1)
        
        password = sys.argv[2]
        redirect_url = sys.argv[3]
        asyncio.run(add_password(password, redirect_url))
        
    elif command == "invite":
        if len(sys.argv) < 4:
            print("Error: invite requires <invite_code> and <redirect_url>")
            sys.exit(1)
        
        invite_code = sys.argv[2]
        redirect_url = sys.argv[3]
        
        parent_id = None
        max_uses = None
        
        # Parse optional arguments
        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--parent-id" and i + 1 < len(sys.argv):
                parent_id = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--max-uses" and i + 1 < len(sys.argv):
                max_uses = int(sys.argv[i + 1])
                i += 2
            else:
                i += 1
        
        asyncio.run(add_invite(invite_code, redirect_url, parent_id, max_uses))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()

