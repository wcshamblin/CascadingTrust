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
    """Initialize database and add test data."""
    # Run async setup synchronously using a helper
    import asyncio

    async def async_setup():
        await init_database()

        # Add a test password node
        db = await get_db_connection()
        try:
            await db.execute(
                """
                INSERT INTO nodes (node_type, value, redirect_url, is_active)
                VALUES ('password', 'testpassword123', 'https://example.com/dashboard', TRUE)
                """
            )
            await db.commit()
        finally:
            await db.close()

    async def async_cleanup():
        # Cleanup: Remove test password
        db = await get_db_connection()
        try:
            await db.execute(
                "DELETE FROM nodes WHERE value = 'testpassword123'"
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
    """Test that password validation takes at least 2 seconds."""
    start_time = time.time()
    response = client.post(
        "/api/validate-password",
        json={"password": "testpassword123"}
    )
    elapsed_time = time.time() - start_time

    assert elapsed_time >= 2.0
    assert response.status_code == 200
