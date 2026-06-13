import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query, status
from data.fictional_patients import FICTIONAL_PATIENTS, PATIENT_MAP
from data.prescriptions import PRESCRIPTIONS
from models.schemas import ErrorResponse, FictionalPatient, PatientSearchResponse, Prescription, UserRole
from services.authz_service import AuthenticatedUser, get_current_user

router = APIRouter()


def _normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_accents.lower().strip()


def _is_authorized_patient_access(current_user: AuthenticatedUser, patient: FictionalPatient) -> bool:
    if current_user["role"] == UserRole.doctor:
        return patient.assigned_doctor_id == current_user["id"]
    if current_user["role"] == UserRole.patient:
        return patient.id == current_user["id"]
    return False


@router.get(
    "/search",
    response_model=PatientSearchResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Token requerido o invalido"},
        403: {"model": ErrorResponse, "description": "Rol sin permisos"},
        422: {"model": ErrorResponse, "description": "Solicitud invalida"},
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
)
def search_patients(
    name: str | None = Query(default=None, description="Filtro parcial por nombre del paciente"),
    dni: str | None = Query(default=None, description="Filtro parcial por DNI del paciente"),
    page: int = Query(default=1, ge=1, description="Pagina a devolver (empieza en 1)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Tamano de pagina"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    if not name and not dni:
        raise HTTPException(status_code=422, detail="Debes enviar al menos un filtro: name o dni")

    normalized_name = _normalize_search_text(name) if name else None
    normalized_dni = _normalize_search_text(dni) if dni else None

    if current_user["role"] == UserRole.doctor:
        candidate_patients = FICTIONAL_PATIENTS
    elif current_user["role"] == UserRole.patient:
        own_patient = PATIENT_MAP.get(current_user["id"])
        candidate_patients = [own_patient] if own_patient else []
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rol sin permisos para buscar pacientes")

    filtered = []
    for patient in candidate_patients:
        patient_name = _normalize_search_text(patient.name)
        patient_dni = _normalize_search_text(patient.dni)

        matches_name = normalized_name in patient_name if normalized_name else True
        matches_dni = normalized_dni in patient_dni if normalized_dni else True

        if matches_name and matches_dni:
            filtered.append(patient)

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size

    return PatientSearchResponse(
        items=filtered[start:end],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/", response_model=list[FictionalPatient])
def list_patients(current_user: AuthenticatedUser = Depends(get_current_user)):
    if current_user["role"] == UserRole.doctor:
        return [p for p in FICTIONAL_PATIENTS if p.assigned_doctor_id == current_user["id"]]

    if current_user["role"] == UserRole.patient:
        own_patient = PATIENT_MAP.get(current_user["id"])
        return [own_patient] if own_patient else []

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rol sin permisos para listar pacientes")


@router.get("/{patient_id}", response_model=FictionalPatient)
def get_patient(patient_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    patient = PATIENT_MAP.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    if not _is_authorized_patient_access(current_user, patient):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver este paciente")

    return patient


@router.get("/{patient_id}/summary")
def get_patient_summary(patient_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    patient = PATIENT_MAP.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    if not _is_authorized_patient_access(current_user, patient):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver este resumen")

    prescriptions = PRESCRIPTIONS.get(patient_id, [])
    return {
        "patient": patient,
        "prescriptions_count": len(prescriptions),
        "latest_prescription": prescriptions[-1] if prescriptions else None,
    }


@router.get("/{patient_id}/prescriptions", response_model=list[Prescription])
def get_patient_prescriptions(patient_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    patient = PATIENT_MAP.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    if not _is_authorized_patient_access(current_user, patient):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver estas prescripciones")

    return PRESCRIPTIONS.get(patient_id, [])
