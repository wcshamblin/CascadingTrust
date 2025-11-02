import pytest
import aiosqlite
import sys
import os
from pathlib import Path

# Add backend directory to path so we can import database module
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from database import init_database, get_db_connection, DATABASE_PATH

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

    # Cleanup: Delete all data from the nodes table
    await db.execute("DELETE FROM nodes")
    await db.commit()

    # Close the connection
    await db.close()

    # Restore original path
    database.DATABASE_PATH = original_path


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
