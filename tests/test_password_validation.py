import pytest
import sys
from pathlib import Path
import time

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app import app
from database import get_db_connection, init_database


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Initialize database and add test data with proper site -> password hierarchy."""
    # Run async setup synchronously using a helper
    import asyncio

    async def async_setup():
        await init_database()

        # First create a site node (root node), then a password under it
        db = await get_db_connection()
        try:
            # Create the parent site node
            await db.execute(
                """
                INSERT INTO nodes (node_type, value, redirect_url, is_active)
                VALUES ('site', 'test-site-for-password', 'https://example.com/dashboard', TRUE)
                """
            )
            await db.commit()
            
            # Get the site_id
            cursor = await db.execute(
                "SELECT id FROM nodes WHERE value = 'test-site-for-password'"
            )
            site = await cursor.fetchone()
            site_id = site['id']
            
            # Create the password node under the site
            await db.execute(
                """
                INSERT INTO nodes (node_type, value, parent_id, is_active)
                VALUES ('password', 'testpassword123', ?, TRUE)
                """,
                (site_id,)
            )
            await db.commit()
        finally:
            await db.close()

    async def async_cleanup():
        # Cleanup: Remove test site (will cascade delete password)
        db = await get_db_connection()
        try:
            await db.execute(
                "DELETE FROM nodes WHERE value = 'test-site-for-password'"
            )
            await db.commit()
        finally:
            await db.close()

    # Run setup
    asyncio.run(async_setup())

    yield

    # Run cleanup
    asyncio.run(async_cleanup())


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_validate_password_valid(client):
    """Test validating a valid password."""
    response = client.post(
        "/api/validate-password",
        json={"password": "testpassword123"}
    )

    assert response.status_code == 200
    assert "redirect_url" in response.json()
    assert "token" in response.json()  # JWT token should be returned
    assert response.json()["redirect_url"] == "https://example.com/dashboard"


def test_validate_password_invalid(client):
    """Test validating an invalid password."""
    response = client.post(
        "/api/validate-password",
        json={"password": "wrongpassword"}
    )

    assert response.status_code == 403
    assert "detail" in response.json()


def test_validate_password_timing(client):
    """Test that password validation takes at least 1.5 seconds."""
    start_time = time.time()
    response = client.post(
        "/api/validate-password",
        json={"password": "testpassword123"}
    )
    elapsed_time = time.time() - start_time

    assert elapsed_time >= 1.5
    assert response.status_code == 200
