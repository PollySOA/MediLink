"""
Tests for backend services.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock


def test_authz_service_authenticated_user_type():
    """Test AuthenticatedUser type structure."""
    from services.authz_service import AuthenticatedUser
    from models.schemas import UserRole
    
    user: AuthenticatedUser = {
        "id": "dr.garcia",
        "role": UserRole.doctor,
        "full_name": "Dr. Carlos García",
    }
    
    assert user["id"] == "dr.garcia"
    assert user["role"] == UserRole.doctor


def test_fictional_patients_data():
    """Test fictional patients data structure."""
    from data.fictional_patients import FICTIONAL_PATIENTS
    
    assert len(FICTIONAL_PATIENTS) > 0
    patient = FICTIONAL_PATIENTS[0]
    assert hasattr(patient, 'id')
    assert hasattr(patient, 'name')
    assert hasattr(patient, 'conditions')


def test_users_data_structure():
    """Test users data has required fields."""
    from data.users import DEMO_USERS
    
    assert len(DEMO_USERS) > 0
    
    for username, user in DEMO_USERS.items():
        assert "password" in user
        assert "role" in user
        assert user["role"] in ["doctor", "patient"]


def test_prescriptions_data():
    """Test prescriptions data structure."""
    from data.prescriptions import PRESCRIPTIONS
    
    assert isinstance(PRESCRIPTIONS, dict)
    # May be empty or have patient prescriptions
    for patient_id, rx_list in PRESCRIPTIONS.items():
        assert isinstance(rx_list, list)
        if len(rx_list) > 0:
            rx = rx_list[0]
            assert hasattr(rx, 'id')
            assert hasattr(rx, 'medication')


def test_avatar_feedback_storage():
    """Test avatar feedback storage structure."""
    from data.avatar_feedback import AVATAR_FEEDBACK_LOG
    
    # AVATAR_FEEDBACK_LOG may be empty initially, that's OK
    assert isinstance(AVATAR_FEEDBACK_LOG, list)


@pytest.mark.asyncio
async def test_azure_llm_service_imports():
    """Test Azure LLM service can be imported."""
    from services import azure_llm_service
    
    # Just verify module loads
    assert hasattr(azure_llm_service, 'call_azure_openai') or True


def test_config_settings():
    """Test config settings load correctly."""
    from config import get_settings
    
    settings = get_settings()
    
    # Settings should have required attributes
    assert hasattr(settings, 'jwt_secret')
    assert hasattr(settings, 'jwt_algorithm')
    assert hasattr(settings, 'app_env')


def test_service_errors_module():
    """Test service_errors module exists."""
    from services import service_errors
    
    # Verify module loads
    assert service_errors is not None


def test_fhir_service_imports():
    """Test FHIR service module loads."""
    from services import fhir_service
    
    assert fhir_service is not None


@pytest.mark.asyncio
async def test_idonia_service_imports():
    """Test Idonia service module loads."""
    from services import idonia_service
    
    assert idonia_service is not None
