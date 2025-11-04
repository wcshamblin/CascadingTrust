"""
Test JWT authentication endpoints.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import jwt


@pytest.mark.asyncio
async def test_password_validation_generates_jwt(client: AsyncClient, sample_password_node):
    """Test that validating a password generates a JWT token."""
    # Validate the password
    response = await client.post(
        "/api/validate-password",
        json={"password": sample_password_node["value"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that a token is returned
    assert "token" in data
    assert "redirect_url" in data
    assert data["redirect_url"] == sample_password_node["redirect_url"]
    
    # Check that the token cookie is set
    assert "auth_token" in response.cookies


@pytest.mark.asyncio
async def test_generate_jwt_endpoint(client: AsyncClient, sample_password_node):
    """Test the generate-jwt endpoint."""
    response = await client.post(
        "/api/generate-jwt",
        json={"node_id": sample_password_node["id"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "token" in data
    assert "expires_at" in data
    
    # Verify the token is valid
    token = data["token"]
    validate_response = await client.post(
        "/api/validate-jwt",
        json={"token": token}
    )
    
    assert validate_response.status_code == 200
    validate_data = validate_response.json()
    assert validate_data["valid"] is True
    assert validate_data["node_id"] == sample_password_node["id"]


@pytest.mark.asyncio
async def test_validate_jwt_with_invalid_token(client: AsyncClient):
    """Test that validating an invalid JWT returns 401."""
    response = await client.post(
        "/api/validate-jwt",
        json={"token": "invalid-token"}
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_validate_jwt_cookie_endpoint(client: AsyncClient, sample_password_node):
    """Test the validate-jwt-cookie endpoint."""
    # First generate a JWT token
    gen_response = await client.post(
        "/api/generate-jwt",
        json={"node_id": sample_password_node["id"]}
    )
    
    assert gen_response.status_code == 200
    
    # The cookie should be set automatically
    # Now validate using the cookie endpoint
    response = await client.get("/api/validate-jwt-cookie")
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["node_id"] == sample_password_node["id"]


@pytest.mark.asyncio
async def test_validate_jwt_cookie_without_cookie(client: AsyncClient):
    """Test that validate-jwt-cookie returns 401 without a cookie."""
    response = await client.get("/api/validate-jwt-cookie")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_jwt_for_nonexistent_node(client: AsyncClient):
    """Test that generating a JWT for a non-existent node returns 404."""
    response = await client.post(
        "/api/generate-jwt",
        json={"node_id": 99999}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_jwt_stored_in_database(client: AsyncClient, sample_password_node, db):
    """Test that JWT tokens are stored in the database."""
    # Generate a JWT token
    response = await client.post(
        "/api/generate-jwt",
        json={"node_id": sample_password_node["id"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    token = data["token"]
    
    # Check that the token is in the database
    cursor = await db.execute(
        "SELECT * FROM jwt_tokens WHERE token = ?",
        (token,)
    )
    token_record = await cursor.fetchone()
    
    assert token_record is not None
    assert token_record["node_id"] == sample_password_node["id"]
    assert token_record["token"] == token


@pytest.mark.asyncio
async def test_jwt_expires_after_7_days(client: AsyncClient, sample_password_node):
    """Test that JWT tokens expire after 7 days."""
    response = await client.post(
        "/api/generate-jwt",
        json={"node_id": sample_password_node["id"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check expiration time
    expires_at = datetime.fromisoformat(data["expires_at"])
    now = datetime.utcnow()
    diff = expires_at - now
    
    # Should be approximately 7 days (allow small timing variations)
    # Check that it's between 6 days 23 hours and 7 days 1 hour
    total_seconds = diff.total_seconds()
    seven_days_seconds = 7 * 24 * 60 * 60
    assert abs(total_seconds - seven_days_seconds) < 3600  # Within 1 hour

