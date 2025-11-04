import aiosqlite
import os
from pathlib import Path
from typing import Optional

DATABASE_PATH = Path(__file__).parent / "db" / "tree.db"


async def get_db_connection() -> aiosqlite.Connection:
    """Get a database connection with WAL mode and foreign keys enabled."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    # Enable foreign key constraints for this connection
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_database() -> None:
    """Initialize the database with tables, indexes, and WAL mode."""
    # Ensure the db directory exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Enable WAL mode for better concurrent access
        await db.execute("PRAGMA journal_mode=WAL")

        # Enable foreign key constraints
        await db.execute("PRAGMA foreign_keys=ON")

        # Create the nodes table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_type TEXT NOT NULL CHECK (node_type IN ('password', 'invite')),
                value TEXT NOT NULL,
                redirect_url TEXT NOT NULL,
                parent_id INTEGER,
                uses INTEGER DEFAULT 0,
                max_uses INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                expires_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES nodes(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for better query performance
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_parent_id ON nodes(parent_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_node_type ON nodes(node_type)
        """)

        # Create index on value for faster lookups
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_value ON nodes(value)
        """)

        # Create index on is_active for filtering active nodes
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_is_active ON nodes(is_active)
        """)

        # Add redirect_url column if it doesn't exist (migration for existing databases)
        # Check if redirect_url column exists
        cursor = await db.execute("PRAGMA table_info(nodes)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'redirect_url' not in column_names:
            # Add the column with a default value for existing rows
            await db.execute("""
                ALTER TABLE nodes ADD COLUMN redirect_url TEXT DEFAULT '/'
            """)
            print("Added redirect_url column to existing nodes table")

        # Create the jwt_tokens table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jwt_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL,
                node_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for jwt_tokens table
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_jwt_tokens_node_id ON jwt_tokens(node_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_jwt_tokens_expires_at ON jwt_tokens(expires_at)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_jwt_tokens_token ON jwt_tokens(token)
        """)

        await db.commit()

        print(f"Database initialized successfully at {DATABASE_PATH}")
        print("WAL mode enabled")
        print("Tables and indexes created")


async def close_db_connection(db: aiosqlite.Connection) -> None:
    """Close a database connection."""
    await db.close()
