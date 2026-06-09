from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    doctor = "doctor"
    patient = "patient"


class ReportComplexity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    full_name: str
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class FictionalPatient(BaseModel):
    id: str
    name: str
    dni: str
    age: int
    gender: Literal["male", "female", "other"]
    conditions: list[str]
    specialty: str
    sample_report: str
    clinical_context: str
    assigned_doctor_id: str


class PatientSearchResponse(BaseModel):
    items: list[FictionalPatient]
    total: int
    page: int
    page_size: int


class Prescription(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    doctor_name: str
    medication: str
    dosage: str
    frequency: str
    duration: str
    instructions: str
    warnings: list[str]
    created_at: datetime
    humanized_instructions: Optional[str] = None


class CreatePrescriptionRequest(BaseModel):
    patient_id: str = Field(..., description="ID del paciente")
    medication: str = Field(..., description="Nombre del medicamento")
    dosage: str = Field(..., description="Dosis (ej: 500mg)")
    frequency: str = Field(..., description="Frecuencia (ej: cada 8 horas)")
    duration: str = Field(..., description="Duración (ej: 7 días)")
    instructions: str = Field(..., description="Instrucciones adicionales del médico")
    warnings: list[str] = Field(default_factory=list, description="Advertencias")


class ProcessReportRequest(BaseModel):
    dictation_report: str = Field(..., min_length=10)
    patient_id: Optional[str] = None
    specialty: Optional[str] = None


class HumanizedReport(BaseModel):
    patient_summary: str
    complexity: ReportComplexity
    key_findings: list[str]
    recommended_actions: str
    disclaimer: str = "Esta información es orientativa. Consulta con tu médico para aclaraciones."
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_summary": "Tu informe muestra cambios femoropatelares por sobrecarga, sin lesion de meniscos ni ligamentos.",
                "complexity": "medium",
                "key_findings": [
                    "Patela alta con indice IS de 1.5",
                    "Fisuras grado II-III en faceta patelar externa",
                    "Sin derrame articular"
                ],
                "recommended_actions": "Comenta estos hallazgos con tu medico para adaptar actividad y seguimiento.",
                "disclaimer": "Esta informacion es orientativa. Consulta con tu medico para aclaraciones."
            }
        }
    )


class FHIRDiagnosticReport(BaseModel):
    resource_type: str = "DiagnosticReport"
    id: str
    status: Literal["registered", "partial", "preliminary", "final"] = "final"
    category: list[dict]
    code: dict
    subject: dict
    effective_datetime: str
    issued: str
    conclusion: str
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "resource_type": "DiagnosticReport",
                "id": "report-pat-002-001",
                "status": "final",
                "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD", "display": "Radiology"}]}],
                "code": {"coding": [{"system": "http://loinc.org", "code": "36643-5", "display": "MRI Knee"}]},
                "subject": {"reference": "Patient/PAT-002", "display": "Carolina Riera Segura"},
                "effective_datetime": "2026-06-09T10:00:00Z",
                "issued": "2026-06-09T10:05:00Z",
                "conclusion": "Cambios femoropatelares compatibles con sobrecarga patelar, sin lesion meniscal ni ligamentosa."
            }
        }
    )


class ProcessedReportResponse(BaseModel):
    report_id: str
    original_text: str
    humanized: HumanizedReport
    fhir_resource: FHIRDiagnosticReport
    idonia_pdf_generated: bool
    created_at: datetime


class IdoniaAccessResponse(BaseModel):
    status: str
    file_id: str
    open_path: str
    resource: Literal["report", "study"]
    magic_link_url: Optional[str] = None
    magic_link_base_url: Optional[str] = None
    magic_link_route: Optional[str] = None
    magic_link_route_urlsafe: Optional[str] = None
    magic_link_pin: Optional[str] = None
    password_control: Optional[dict] = None
    created_at: datetime
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "file_id": "67198fad-95fc-4e8e-8edb-d6a10e81995a",
                "open_path": "/api/reports/idonia/open/55f832f76ef44353b2739ca676f72121",
                "resource": "report",
                "magic_link_url": "https://staging.idonia.com/v/hacknum23",
                "magic_link_base_url": "https://staging.idonia.com/v/hacknum23",
                "magic_link_route": "Traslados desde Asturias/D210105597",
                "magic_link_route_urlsafe": "Traslados%20desde%20Asturias%2FD210105597",
                "magic_link_pin": "ZCBP7",
                "password_control": {"enabled": True},
                "created_at": "2026-06-09T10:30:00Z"
            }
        }
    )


class AvatarMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Mensaje del paciente al asistente orientativo IA")
    patient_id: str
    conversation_history: list[dict] = Field(default_factory=list)
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Tengo miedo, puedo volver a caminar por la montana?",
                "patient_id": "PAT-002",
                "conversation_history": [
                    {"role": "assistant", "content": "Hola Carolina, estoy aqui para explicarte tu informe."}
                ]
            }
        }
    )


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[object] = None
    trace_id: str
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "http_403",
                "message": "No tienes permiso para ver este paciente",
                "details": None,
                "trace_id": "4c8398f1f0fc44d7a20d6d7822a5f205"
            }
        }
    )


class AvatarMessageResponse(BaseModel):
    justificacion_seguridad: str
    respuesta_voz: str


class AvatarFeedbackRequest(BaseModel):
    patient_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=500)


class AvatarFeedbackResponse(BaseModel):
    status: str
    message: str
    average_rating: Optional[float] = None
    total_ratings: int


class AvatarFeedbackSummary(BaseModel):
    patient_id: Optional[str] = None
    total_ratings: int
    average_rating: Optional[float] = None
    ratings_breakdown: dict[str, int]


class PacienteDemo(BaseModel):
    nombre: str = Field(..., examples=["Carolina Riera Segura"])
    dni: str = Field(..., examples=["D210105597"])
    especialidad: str = Field(..., examples=["Traumatología"])
    diagnostico_corto: str = Field(..., examples=["Lesión de rodilla - Picos de Europa"])


class AudioPregunta(BaseModel):
    paciente_dni: str
    audio_base64: str
