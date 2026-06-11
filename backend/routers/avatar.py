from fastapi import APIRouter, HTTPException, Query
from models.schemas import (
    AvatarFeedbackRequest,
    AvatarFeedbackResponse,
    AvatarFeedbackSummary,
    AvatarMessageRequest,
    AvatarMessageResponse,
)
from data.avatar_feedback import build_avatar_feedback_summary, record_avatar_feedback
from data.fictional_patients import PATIENT_MAP
from data.prescriptions import PRESCRIPTIONS
from services.avatar_service import chat_avatar_elena
from services.service_errors import ServiceError

router = APIRouter()


def _build_patient_context(patient_id: str) -> tuple[object, dict]:
    patient = PATIENT_MAP.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    prescriptions = PRESCRIPTIONS.get(patient_id, [])
    patient_context = {
        "name": patient.name,
        "age": patient.age,
        "conditions": patient.conditions,
        "specialty": patient.specialty,
        "clinical_context": patient.clinical_context,
        "has_report": True,
        "has_prescription": len(prescriptions) > 0,
        "official_report": patient.sample_report,
        "report_summary": patient.sample_report,
        "latest_prescription": (
            f"{prescriptions[-1].medication} {prescriptions[-1].dosage} — {prescriptions[-1].frequency}"
            if prescriptions else None
        ),
    }
    return patient, patient_context


@router.post("/chat", response_model=AvatarMessageResponse)
async def avatar_chat(body: AvatarMessageRequest):
    patient, patient_context = _build_patient_context(body.patient_id)

    try:
        return await chat_avatar_elena(
            patient_context=patient_context,
            conversation_history=body.conversation_history,
            user_message=body.message,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc


@router.get("/greeting/{patient_id}", response_model=AvatarMessageResponse)
async def avatar_greeting(patient_id: str):
    patient, patient_context = _build_patient_context(patient_id)
    try:
        return await chat_avatar_elena(
            patient_context=patient_context,
            conversation_history=[],
            user_message=f"Hola, soy {patient.name}. Acabo de entrar.",
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc


@router.post("/feedback", response_model=AvatarFeedbackResponse)
async def avatar_feedback(body: AvatarFeedbackRequest):
    patient = PATIENT_MAP.get(body.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    clean_comment = body.comment.strip() if body.comment else None
    record_avatar_feedback(patient_id=body.patient_id, rating=body.rating, comment=clean_comment or None)
    summary = build_avatar_feedback_summary(body.patient_id)
    return AvatarFeedbackResponse(
        status="ok",
        message="Gracias por valorar la ayuda de Elena.",
        average_rating=summary["average_rating"],
        total_ratings=summary["total_ratings"],
    )


@router.get("/feedback/summary", response_model=AvatarFeedbackSummary)
async def avatar_feedback_summary(patient_id: str | None = Query(default=None)):
    return AvatarFeedbackSummary(**build_avatar_feedback_summary(patient_id))
