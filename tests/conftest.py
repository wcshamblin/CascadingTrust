import pytest
import aiosqlite
import sys
import os
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Add backend directory to path so we can import database module
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from database import init_database, get_db_connection, DATABASE_PATH
from app import app

# Use a test database
TEST_DB_PATH = Path(__file__).parent / "test_tree.db"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for pytest-asyncio."""
    import asyncio
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="function")
async def test_db():
    """
    Provides a clean database connection for each test.
    Automatically cleans up all data after the test completes.
    """
    # Override the DATABASE_PATH temporarily
    import database
    original_path = database.DATABASE_PATH
    database.DATABASE_PATH = TEST_DB_PATH

    # Initialize the test database
    await init_database()

    # Provide the database connection
    db = await get_db_connection()

    yield db

    # Cleanup: Delete all data from the tables
    await db.execute("DELETE FROM jwt_tokens")
    await db.execute("DELETE FROM nodes")
    await db.commit()

    # Close the connection
    await db.close()

    # Restore original path
    database.DATABASE_PATH = original_path


@pytest.fixture(scope="function")
async def db(test_db):
    """Alias for test_db fixture for easier use."""
    return test_db


@pytest.fixture(scope="function")
async def client(test_db):
    """
    Provides an async HTTP client for testing the FastAPI app.
    """
    # Override DATABASE_PATH for the app
    import database
    original_path = database.DATABASE_PATH
    database.DATABASE_PATH = TEST_DB_PATH

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    # Restore original path
    database.DATABASE_PATH = original_path


@pytest.fixture(scope="function")
async def sample_site_node(test_db):
    """
    Creates a sample site node in the database for testing.
    Site nodes are root nodes in the hierarchy.
    """
    # Insert a sample site node
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, redirect_url, is_active)
        VALUES (?, ?, ?, ?)
        """,
        ("site", "test-site", "https://example.com/dashboard", True)
    )
    await test_db.commit()

    # Retrieve the created node
    cursor = await test_db.execute(
        "SELECT * FROM nodes WHERE value = ?",
        ("test-site",)
    )
    node = await cursor.fetchone()

    # Convert to dict for easier access
    return {
        "id": node["id"],
        "node_type": node["node_type"],
        "value": node["value"],
        "redirect_url": node["redirect_url"],
        "is_active": node["is_active"],
    }


@pytest.fixture(scope="function")
async def sample_password_node(test_db, sample_site_node):
    """
    Creates a sample password node in the database for testing.
    Password nodes must have a parent site node for site-scoped tokens.
    """
    site_id = sample_site_node["id"]
    
    # Insert a sample password node with parent site
    await test_db.execute(
        """
        INSERT INTO nodes (node_type, value, parent_id, is_active)
        VALUES (?, ?, ?, ?)
        """,
        ("password", "test-password-123", site_id, True)
    )
    await test_db.commit()

    # Retrieve the created node
    cursor = await test_db.execute(
        "SELECT * FROM nodes WHERE value = ?",
        ("test-password-123",)
    )
    node = await cursor.fetchone()

    # Convert to dict for easier access
    return {
        "id": node["id"],
        "node_type": node["node_type"],
        "value": node["value"],
        "redirect_url": sample_site_node["redirect_url"],  # Redirect URL comes from parent site
        "parent_id": node["parent_id"],
        "site_id": site_id,
        "is_active": node["is_active"],
    }


def pytest_sessionfinish(session, exitstatus):
    """
    Removes the test database file after all tests complete.
    This is a pytest hook that runs after the test session.
    """
    # Remove test database file if it exists
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    # Also remove WAL files
    wal_path = Path(str(TEST_DB_PATH) + "-wal")
    shm_path = Path(str(TEST_DB_PATH) + "-shm")

    if wal_path.exists():
        wal_path.unlink()
    if shm_path.exists():
        shm_path.unlink()
