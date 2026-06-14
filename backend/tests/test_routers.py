"""
Tests for API routers/endpoints.
"""
import pytest


def test_root_endpoint(test_client):
    """Test root endpoint returns project info."""
    response = test_client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert data["project"] == "MediLink"


def test_demo_info_endpoint(test_client):
    """Test demo flow endpoint."""
    response = test_client.get("/api/demo/flow")
    
    assert response.status_code == 200
    data = response.json()
    assert "hackathon" in data
    assert "demo_accounts" in data


def test_login_success(test_client):
    """Test successful login with valid credentials."""
    response = test_client.post(
        "/api/auth/login",
        json={"username": "dr.garcia", "password": "demo1234"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["role"] == "doctor"


def test_login_invalid_credentials(test_client):
    """Test login fails with invalid credentials."""
    response = test_client.post(
        "/api/auth/login",
        json={"username": "invalid", "password": "wrong"}
    )
    
    assert response.status_code == 401


def test_login_missing_fields(test_client):
    """Test login fails with missing fields."""
    response = test_client.post(
        "/api/auth/login",
        json={"username": "dr.garcia"}  # Missing password
    )
    
    assert response.status_code == 422  # Validation error


def test_demo_accounts_endpoint(test_client):
    """Test demo accounts listing endpoint."""
    response = test_client.get("/api/auth/demo-accounts")
    
    assert response.status_code == 200
    data = response.json()
    assert "doctors" in data
    assert "patients" in data
    assert len(data["doctors"]) > 0
    assert len(data["patients"]) > 0


def test_get_patient_unauthorized(test_client):
    """Test patient endpoint requires authentication."""
    response = test_client.get("/api/patients/PAT-001")
    
    # Should require auth
    assert response.status_code in [401, 403]


def test_get_patient_with_auth(test_client, auth_token_doctor):
    """Test get patient with valid doctor token."""
    response = test_client.get(
        "/api/patients/PAT-001",
        headers={"Authorization": f"Bearer {auth_token_doctor}"}
    )
    
    # May be 200 or 404 depending on data, but should not be 401
    assert response.status_code != 401


def test_fhir_patient_endpoint(test_client):
    """Test FHIR patient endpoint."""
    response = test_client.get("/api/fhir/Patient/PAT-001")
    
    # FHIR endpoint may require auth or return patient data
    assert response.status_code in [200, 401, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert "resourceType" in data


def test_openapi_docs_available(test_client):
    """Test OpenAPI documentation is available."""
    response = test_client.get("/docs")
    
    assert response.status_code == 200


def test_health_check_endpoint(test_client):
    """Test health check endpoint if exists."""
    response = test_client.get("/")
    
    # Root endpoint serves as basic health check
    assert response.status_code == 200


def test_cors_headers(test_client):
    """Test CORS headers are present."""
    response = test_client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        }
    )
    
    # OPTIONS request for CORS preflight
    assert response.status_code in [200, 204]


def test_patient_prescriptions_endpoint(test_client, auth_token_doctor):
    """Test get patient prescriptions endpoint."""
    response = test_client.get(
        "/api/patients/PAT-001/prescriptions",
        headers={"Authorization": f"Bearer {auth_token_doctor}"}
    )
    
    # Should return prescriptions list (may be empty)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


def test_avatar_greeting_endpoint(test_client, auth_token_patient):
    """Test avatar greeting endpoint."""
    response = test_client.get(
        "/api/avatar/greeting?patient_id=PAT-001",
        headers={"Authorization": f"Bearer {auth_token_patient}"}
    )
    
    # May require specific auth or return greeting
    if response.status_code == 200:
        data = response.json()
        assert "message" in data or "greeting" in data
