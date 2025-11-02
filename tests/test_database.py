import pytest
from datetime import datetime, timedelta
from pathlib import Path


@pytest.mark.asyncio
async def test_database_initialization(test_db):
    """
    Verifies that init_database() creates the database file,
    the nodes table exists, WAL mode is enabled, and foreign keys work.
    """
    # Check that database file exists
    from conftest import TEST_DB_PATH
    assert TEST_DB_PATH.exists()

    # Check WAL mode
    cursor = await test_db.execute("PRAGMA journal_mode")
    result = await cursor.fetchone()
    assert result[0].lower() == "wal"

    # Check that nodes table exists
    cursor = await test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'"
    )
    result = await cursor.fetchone()
    assert result is not None
    assert result[0] == "nodes"


@pytest.mark.asyncio
async def test_nodes_table_schema(test_db):
    """
    Validates all required columns exist with correct data types.
    """
    cursor = await test_db.execute("PRAGMA table_info(nodes)")
    columns = await cursor.fetchall()

    column_dict = {col[1]: col[2] for col in columns}

    # Verify all required columns exist
    required_columns = {
        "id": "INTEGER",
        "node_type": "TEXT",
        "value": "TEXT",
        "redirect_url": "TEXT",
        "parent_id": "INTEGER",
        "uses": "INTEGER",
        "max_uses": "INTEGER",
        "is_active": "BOOLEAN",
        "expires_at": "DATETIME",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    }

    for col_name, col_type in required_columns.items():
        assert col_name in column_dict
        assert column_dict[col_name] == col_type


@pytest.mark.asyncio
async def test_required_indexes(test_db):
    """
    Confirms all required indexes are created.
    """
    cursor = await test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='nodes'"
    )
    indexes = await cursor.fetchall()
    index_names = [idx[0] for idx in indexes]

    # Check for required indexes
    required_indexes = [
        "idx_parent_id",
        "idx_node_type",
        "idx_value",
        "idx_is_active",
    ]

    for idx_name in required_indexes:
        assert idx_name in index_names


@pytest.mark.asyncio
async def test_insert_password_node(test_db):
    """
    Inserts a password node without a parent and verifies default values.
    """
    # Insert password node
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url)
        VALUES ('password', 'test_password_123', 'https://example.com')
        """
    )
    await test_db.commit()

    # Verify the insert
    cursor = await test_db.execute(
        "SELECT * FROM nodes WHERE node_type='password' AND value='test_password_123'"
    )
    row = await cursor.fetchone()

    assert row is not None
    assert row["node_type"] == "password"
    assert row["value"] == "test_password_123"
    assert row["redirect_url"] == "https://example.com"
    assert row["parent_id"] is None  # Root node has no parent
    assert row["uses"] == 0  # Default value
    assert row["is_active"] == 1  # TRUE (SQLite stores as 1)
    assert row["created_at"] is not None


@pytest.mark.asyncio
async def test_insert_invite_node(test_db):
    """
    Creates an invite linked to a parent password and verifies the relationship.
    """
    # First, insert a password node
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url)
        VALUES ('password', 'parent_password', 'https://parent.com')
        """
    )
    await test_db.commit()

    cursor = await test_db.execute("SELECT id FROM nodes WHERE value='parent_password'")
    parent = await cursor.fetchone()
    parent_id = parent["id"]

    # Insert invite node with parent
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url, parent_id, max_uses)
        VALUES ('invite', 'invite_code_xyz', 'https://invite.com', ?, 10)
        """,
        (parent_id,),
    )
    await test_db.commit()

    # Verify the invite
    cursor = await test_db.execute(
        "SELECT * FROM nodes WHERE node_type='invite' AND value='invite_code_xyz'"
    )
    row = await cursor.fetchone()

    assert row is not None
    assert row["node_type"] == "invite"
    assert row["value"] == "invite_code_xyz"
    assert row["redirect_url"] == "https://invite.com"
    assert row["parent_id"] == parent_id
    assert row["max_uses"] == 10


@pytest.mark.asyncio
async def test_node_type_constraint(test_db):
    """
    Attempts to insert a node with invalid node_type and ensures it's rejected.
    """
    with pytest.raises(Exception):  # Should raise integrity error
        await test_db.execute(
            """
            INSERT INTO nodes (node_type, value, redirect_url)
            VALUES ('invalid_type', 'test_value', 'https://test.com')
            """
        )
        await test_db.commit()


@pytest.mark.asyncio
async def test_cascade_delete(test_db):
    """
    Creates a parent password with child invites, deletes the parent,
    and verifies children are automatically deleted via CASCADE.
    """
    # Insert parent password
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url)
        VALUES ('password', 'parent_to_delete', 'https://delete.com')
        """
    )
    await test_db.commit()

    cursor = await test_db.execute(
        "SELECT id FROM nodes WHERE value='parent_to_delete'"
    )
    parent = await cursor.fetchone()
    parent_id = parent["id"]

    # Insert multiple child invites
    for i in range(3):
        await test_db.execute(
            """
            INSERT INTO nodes (node_type, value, redirect_url, parent_id)
            VALUES ('invite', ?, ?, ?)
            """,
            (f"child_invite_{i}", f"https://child{i}.com", parent_id),
        )
    await test_db.commit()

    # Verify children exist
    cursor = await test_db.execute(
        "SELECT COUNT(*) FROM nodes WHERE parent_id=?", (parent_id,)
    )
    count = await cursor.fetchone()
    assert count[0] == 3

    # Delete parent
    await test_db.execute("DELETE FROM nodes WHERE id=?", (parent_id,))
    await test_db.commit()

    # Verify children are also deleted
    cursor = await test_db.execute(
        "SELECT COUNT(*) FROM nodes WHERE parent_id=?", (parent_id,)
    )
    count = await cursor.fetchone()
    assert count[0] == 0


@pytest.mark.asyncio
async def test_update_node_uses(test_db):
    """
    Increments the uses counter for a node and verifies it persists.
    """
    # Insert a node
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url)
        VALUES ('invite', 'usage_test_invite', 'https://usage.com')
        """
    )
    await test_db.commit()

    # Get the node ID
    cursor = await test_db.execute(
        "SELECT id, uses FROM nodes WHERE value='usage_test_invite'"
    )
    row = await cursor.fetchone()
    node_id = row["id"]
    initial_uses = row["uses"]

    # Increment uses
    await test_db.execute(
        "UPDATE nodes SET uses = uses + 1 WHERE id=?", (node_id,)
    )
    await test_db.commit()

    # Verify the update
    cursor = await test_db.execute("SELECT uses FROM nodes WHERE id=?", (node_id,))
    row = await cursor.fetchone()
    assert row["uses"] == initial_uses + 1


@pytest.mark.asyncio
async def test_max_uses_logic(test_db):
    """
    Tests logic for checking if a node has reached max_uses.
    """
    # Insert node with max_uses
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url, uses, max_uses)
        VALUES ('invite', 'limited_invite', 'https://limited.com', 2, 5)
        """
    )
    await test_db.commit()

    # Query nodes where uses < max_uses (should have remaining uses)
    cursor = await test_db.execute(
        """
        SELECT * FROM nodes
        WHERE value='limited_invite' AND uses < max_uses
        """
    )
    row = await cursor.fetchone()
    assert row is not None  # Should find the node

    # Update uses to reach max
    await test_db.execute(
        "UPDATE nodes SET uses = 5 WHERE value='limited_invite'"
    )
    await test_db.commit()

    # Query again - should not find it now
    cursor = await test_db.execute(
        """
        SELECT * FROM nodes
        WHERE value='limited_invite' AND uses < max_uses
        """
    )
    row = await cursor.fetchone()
    assert row is None  # Should not find it (uses >= max_uses)


@pytest.mark.asyncio
async def test_active_inactive_filtering(test_db):
    """
    Inserts active and inactive nodes and queries for only active ones.
    """
    # Insert active node
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url, is_active)
        VALUES ('password', 'active_password', 'https://active.com', TRUE)
        """
    )

    # Insert inactive node
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url, is_active)
        VALUES ('password', 'inactive_password', 'https://inactive.com', FALSE)
        """
    )
    await test_db.commit()

    # Query only active nodes
    cursor = await test_db.execute(
        "SELECT value FROM nodes WHERE is_active = TRUE"
    )
    rows = await cursor.fetchall()
    values = [row["value"] for row in rows]

    assert "active_password" in values
    assert "inactive_password" not in values


@pytest.mark.asyncio
async def test_expiration_logic(test_db):
    """
    Inserts nodes with expires_at in the past and future,
    verifies queries can filter by expiration date.
    """
    now = datetime.now()
    past_time = (now - timedelta(days=1)).isoformat()
    future_time = (now + timedelta(days=1)).isoformat()

    # Insert expired node
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url, expires_at)
        VALUES ('invite', 'expired_invite', 'https://expired.com', ?)
        """,
        (past_time,),
    )

    # Insert valid (not expired) node
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url, expires_at)
        VALUES ('invite', 'valid_invite', 'https://valid.com', ?)
        """,
        (future_time,),
    )

    # Insert node with no expiration
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url, expires_at)
        VALUES ('invite', 'never_expires', 'https://never.com', NULL)
        """
    )
    await test_db.commit()

    # Query non-expired nodes
    cursor = await test_db.execute(
        """
        SELECT value FROM nodes
        WHERE expires_at IS NULL OR expires_at > ?
        """,
        (now.isoformat(),),
    )
    rows = await cursor.fetchall()
    values = [row["value"] for row in rows]

    assert "valid_invite" in values
    assert "never_expires" in values
    assert "expired_invite" not in values


@pytest.mark.asyncio
async def test_multiple_root_passwords(test_db):
    """
    Creates multiple password nodes without parents and verifies they coexist.
    """
    # Insert multiple root passwords
    passwords = ["password1", "password2", "password3"]
    for i, pwd in enumerate(passwords):
        await test_db.execute(
            """
            INSERT INTO nodes (node_type, value, redirect_url)
            VALUES ('password', ?, ?)
            """,
            (pwd, f"https://password{i+1}.com"),
        )
    await test_db.commit()

    # Query all root passwords (no parent)
    cursor = await test_db.execute(
        """
        SELECT value FROM nodes
        WHERE node_type='password' AND parent_id IS NULL
        """
    )
    rows = await cursor.fetchall()
    values = [row["value"] for row in rows]

    assert len(values) == 3
    for pwd in passwords:
        assert pwd in values


@pytest.mark.asyncio
async def test_deep_node_hierarchy(test_db):
    """
    Creates a password → invite → invite chain to verify multi-level relationships.
    """
    # Insert root password
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url)
        VALUES ('password', 'root_password', 'https://root.com')
        """
    )
    await test_db.commit()

    cursor = await test_db.execute("SELECT id FROM nodes WHERE value='root_password'")
    root_id = (await cursor.fetchone())["id"]

    # Insert first-level invite
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url, parent_id)
        VALUES ('invite', 'level1_invite', 'https://level1.com', ?)
        """,
        (root_id,),
    )
    await test_db.commit()

    cursor = await test_db.execute("SELECT id FROM nodes WHERE value='level1_invite'")
    level1_id = (await cursor.fetchone())["id"]

    # Insert second-level invite (child of invite)
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url, parent_id)
        VALUES ('invite', 'level2_invite', 'https://level2.com', ?)
        """,
        (level1_id,),
    )
    await test_db.commit()

    # Verify the hierarchy
    cursor = await test_db.execute(
        """
        SELECT n1.value as root, n2.value as level1, n3.value as level2
        FROM nodes n1
        LEFT JOIN nodes n2 ON n2.parent_id = n1.id
        LEFT JOIN nodes n3 ON n3.parent_id = n2.id
        WHERE n1.value = 'root_password'
        """
    )
    row = await cursor.fetchone()

    assert row["root"] == "root_password"
    assert row["level1"] == "level1_invite"
    assert row["level2"] == "level2_invite"
