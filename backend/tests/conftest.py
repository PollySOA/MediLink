"""
Pytest configuration and shared fixtures for MediLink backend tests.
"""
import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to import backend modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Ensure backend startup validation does not fail during tests.
os.environ.setdefault("IDONIA_API_SECRET", "S2-test-secret")
os.environ.setdefault("RECOG_API_KEY", "rrk_test_testsecret")
os.environ.setdefault("RECOG_STRICT_MODE", "true")
os.environ.setdefault("JWT_SECRET", "test-secret-key")


@pytest.fixture
def test_client():
    """FastAPI test client fixture."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from config import Settings
    return Settings(
        jwt_secret="test-secret-key",
        idonia_api_key="test-key",
        idonia_api_secret="test-secret",
        azure_openai_api_key="test-azure-key",
        azure_openai_endpoint="https://test.openai.azure.com/",
    )


@pytest.fixture
def sample_patient_data():
    """Sample patient data for tests."""
    return {
        "id": "PAT-001",
        "name": "Alejandro Martín",
        "birth_date": "1985-06-15",
        "gender": "M",
        "nhc": "NH12345",
        "diagnosis": "Rotura menisco interno rodilla izquierda",
    }


@pytest.fixture
def sample_prescription_data():
    """Sample prescription data for tests."""
    return {
        "id": "RX-001",
        "patient_id": "PAT-001",
        "medication": "Ibuprofeno 600mg",
        "dosage": "1 comprimido cada 8 horas",
        "duration": "7 días",
        "doctor": "Dr. Carlos García",
    }


@pytest.fixture
def auth_token_doctor():
    """Generate valid JWT token for doctor role."""
    from jose import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "sub": "DOC-001",
        "role": "doctor",
        "name": "Dr. Carlos García",
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


@pytest.fixture
def auth_token_patient():
    """Generate valid JWT token for patient role."""
    from jose import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "sub": "PAT-001",
        "role": "patient",
        "name": "Carmen Rodríguez Vega",
        "patient_id": "PAT-001",
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")
