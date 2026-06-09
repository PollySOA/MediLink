import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.schemas import CreatePrescriptionRequest, ErrorResponse, Prescription
from data.fictional_patients import PATIENT_MAP
from data.prescriptions import PRESCRIPTIONS
from data.users import USER_BY_ID
from services.authz_service import AuthenticatedUser, get_current_doctor
from services.azure_llm_service import humanize_prescription

router = APIRouter()


@router.get(
    "/patients",
    responses={
        401: {"model": ErrorResponse, "description": "Token requerido o invalido"},
        403: {"model": ErrorResponse, "description": "Acceso restringido a medicos"},
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
)
def get_doctor_patients(
    doctor_id: str | None = Query(default=None, deprecated=True),
    current_doctor: AuthenticatedUser = Depends(get_current_doctor),
):
    if doctor_id and doctor_id != current_doctor["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes consultar pacientes de otro medico")

    return [p for p in PATIENT_MAP.values() if p.assigned_doctor_id == current_doctor["id"]]


@router.post("/prescriptions", response_model=Prescription)
async def create_prescription(
    body: CreatePrescriptionRequest,
    doctor_id: str | None = Query(default=None, deprecated=True),
    current_doctor: AuthenticatedUser = Depends(get_current_doctor),
):
    if doctor_id and doctor_id != current_doctor["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes crear prescripciones para otro medico")

    if body.patient_id not in PATIENT_MAP:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    patient = PATIENT_MAP[body.patient_id]
    if patient.assigned_doctor_id != current_doctor["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes prescribir a tus pacientes asignados")

    doctor = USER_BY_ID.get(current_doctor["id"])
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    humanized = await humanize_prescription({
        "medication": body.medication,
        "dosage": body.dosage,
        "frequency": body.frequency,
        "duration": body.duration,
        "instructions": body.instructions,
        "warnings": body.warnings,
    })

    prescription = Prescription(
        id=f"RX-{uuid.uuid4().hex[:6].upper()}",
        patient_id=body.patient_id,
        doctor_id=current_doctor["id"],
        doctor_name=doctor["full_name"],
        medication=body.medication,
        dosage=body.dosage,
        frequency=body.frequency,
        duration=body.duration,
        instructions=body.instructions,
        warnings=body.warnings,
        created_at=datetime.now(timezone.utc),
        humanized_instructions=humanized,
    )

    if body.patient_id not in PRESCRIPTIONS:
        PRESCRIPTIONS[body.patient_id] = []
    PRESCRIPTIONS[body.patient_id].append(prescription)

    return prescription


@router.get("/prescriptions/{patient_id}", response_model=list[Prescription])
def get_patient_prescriptions(patient_id: str, current_doctor: AuthenticatedUser = Depends(get_current_doctor)):
    patient = PATIENT_MAP.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    if patient.assigned_doctor_id != current_doctor["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes consultar prescripciones de otro medico")

    return PRESCRIPTIONS.get(patient_id, [])
