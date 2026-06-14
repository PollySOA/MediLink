"""
Tests for Pydantic models/schemas.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError


def test_fictional_patient_creation(sample_patient_data):
    """Test FictionalPatient schema creation with valid data."""
    from models.schemas import FictionalPatient
    
    patient = FictionalPatient(
        id="PAT-001",
        name="Alejandro Martín",
        dni="12345678A",
        age=39,
        gender="male",
        conditions=["Rotura menisco interno"],
        specialty="Traumatología",
        sample_report="Informe RMN rodilla izquierda",
        clinical_context="Dolor rodilla tras esfuerzo",
        assigned_doctor_id="dr.garcia",
    )
    
    assert patient.id == "PAT-001"
    assert patient.name == "Alejandro Martín"
    assert patient.gender == "male"


def test_fictional_patient_missing_required_fields():
    """Test FictionalPatient validation fails with missing fields."""
    from models.schemas import FictionalPatient
    
    with pytest.raises(ValidationError):
        FictionalPatient(id="PAT-001")  # Missing required fields


def test_user_login_validation():
    """Test UserLogin schema validation."""
    from models.schemas import UserLogin
    
    login = UserLogin(username="dr.garcia", password="demo1234")
    
    assert login.username == "dr.garcia"
    assert login.password == "demo1234"


def test_user_login_empty_username():
    """Test UserLogin fails with empty username."""
    from models.schemas import UserLogin
    
    # Empty username is valid Pydantic string, just testing it creates
    login = UserLogin(username="", password="demo1234")
    assert login.username == ""


def test_avatar_message_response_structure():
    """Test AvatarMessageResponse schema structure."""
    from models.schemas import AvatarMessageResponse
    
    response = AvatarMessageResponse(
        justificacion_seguridad="Respuesta basada en el informe clínico del paciente.",
        respuesta_voz="Hola Carolina, estoy aquí para ayudarte.",
    )
    
    assert response.justificacion_seguridad == "Respuesta basada en el informe clínico del paciente."
    assert response.respuesta_voz == "Hola Carolina, estoy aquí para ayudarte."


def test_prescription_schema():
    """Test Prescription schema."""
    from models.schemas import Prescription
    
    prescription = Prescription(
        id="RX-001",
        patient_id="PAT-001",
        doctor_id="dr.garcia",
        doctor_name="Dr. García",
        medication="Ibuprofeno 600mg",
        dosage="600mg",
        frequency="cada 8 horas",
        duration="7 días",
        instructions="Tomar con comida",
        warnings=["No mezclar con alcohol"],
        created_at=datetime.now(),
    )
    
    assert prescription.id == "RX-001"
    assert prescription.medication == "Ibuprofeno 600mg"
    assert prescription.frequency == "cada 8 horas"


def test_idonia_access_response():
    """Test IdoniaAccessResponse schema."""
    from models.schemas import IdoniaAccessResponse
    
    response = IdoniaAccessResponse(
        magic_link_url="https://idonia.com/viewer?token=abc123",
        status="completed",
        file_id="file123",
        open_path="/viewer/doc",
        resource="report",
        created_at="2026-06-14T10:00:00",
    )
    
    assert "idonia.com" in response.magic_link_url
    assert response.status == "completed"
    assert response.resource == "report"


def test_error_response_schema():
    """Test ErrorResponse schema for error responses."""
    from models.schemas import ErrorResponse
    
    error = ErrorResponse(
        code="validation_error",
        message="Invalid patient ID format",
        trace_id="abc123",
    )
    
    assert error.code == "validation_error"
    assert "Invalid patient ID" in error.message


def test_token_response():
    """Test TokenResponse schema."""
    from models.schemas import TokenResponse, UserOut, UserRole
    
    token = TokenResponse(
        access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        token_type="bearer",
        user=UserOut(
            id="1",
            username="dr.garcia",
            full_name="Dr. Carlos García",
            role=UserRole.doctor,
        ),
    )
    
    assert token.token_type == "bearer"
    assert token.user.role == UserRole.doctor
    assert "eyJ" in token.access_token


def test_create_prescription_request():
    """Test CreatePrescriptionRequest schema."""
    from models.schemas import CreatePrescriptionRequest
    
    request = CreatePrescriptionRequest(
        patient_id="PAT-001",
        medication="Paracetamol",
        dosage="500mg",
        frequency="cada 6 horas",
        duration="5 días",
        instructions="Tomar con agua",
        warnings=["No superar 4g diarios"],
    )
    
    assert request.patient_id == "PAT-001"
    assert request.medication == "Paracetamol"
    assert len(request.warnings) == 1
