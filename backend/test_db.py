import asyncio
from database import init_database, get_db_connection, DATABASE_PATH


async def test_database():
    """Test database creation and verify schema."""
    print("Testing database initialization...")

    # Initialize the database
    await init_database()

    # Connect and verify the schema
    db = await get_db_connection()

    try:
        # Check WAL mode
        cursor = await db.execute("PRAGMA journal_mode")
        journal_mode = await cursor.fetchone()
        print(f"Journal mode: {journal_mode[0]}")

        # Check foreign keys
        cursor = await db.execute("PRAGMA foreign_keys")
        foreign_keys = await cursor.fetchone()
        print(f"Foreign keys enabled: {bool(foreign_keys[0])}")

        # Verify nodes table exists and check its structure
        cursor = await db.execute("PRAGMA table_info(nodes)")
        columns = await cursor.fetchall()
        print("\nNodes table columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        # Verify indexes
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='nodes'")
        indexes = await cursor.fetchall()
        print("\nIndexes on nodes table:")
        for idx in indexes:
            print(f"  - {idx[0]}")

        # Test inserting a sample password node
        await db.execute("""
            INSERT INTO nodes (node_type, value, is_active)
            VALUES ('password', 'test_password_123', TRUE)
        """)
        await db.commit()

        # Verify the insert
        cursor = await db.execute("SELECT * FROM nodes WHERE node_type='password'")
        row = await cursor.fetchone()
        print("\nSample password node inserted:")
        print(f"  ID: {row['id']}")
        print(f"  Type: {row['node_type']}")
        print(f"  Value: {row['value']}")
        print(f"  Active: {row['is_active']}")
        print(f"  Created at: {row['created_at']}")

        # Test inserting an invite linked to the password
        await db.execute("""
            INSERT INTO nodes (node_type, value, parent_id, is_active, max_uses)
            VALUES ('invite', 'invite_code_abc', ?, TRUE, 5)
        """, (row['id'],))
        await db.commit()

        # Verify the invite
        cursor = await db.execute("SELECT * FROM nodes WHERE node_type='invite'")
        invite_row = await cursor.fetchone()
        print("\nSample invite node inserted:")
        print(f"  ID: {invite_row['id']}")
        print(f"  Type: {invite_row['node_type']}")
        print(f"  Value: {invite_row['value']}")
        print(f"  Parent ID: {invite_row['parent_id']}")
        print(f"  Max uses: {invite_row['max_uses']}")

        print("\n✓ Database test completed successfully!")
        print(f"✓ Database created at: {DATABASE_PATH}")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(test_database())
