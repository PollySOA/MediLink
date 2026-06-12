import asyncio
import io
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, Response

from config import get_settings
from data.fictional_patients import PATIENT_MAP
from models.schemas import HumanizedReport, ProcessReportRequest, ProcessedReportResponse
from models.schemas import IdoniaAccessResponse, UserRole
from services.azure_llm_service import extract_fhir_fields, humanize_report
from services.authz_service import AuthenticatedUser, get_current_user
from services.fhir_service import build_diagnostic_report
from services.idonia_service import (
    calcular_password_hash_idonia,
    descargar_archivo_idonia,
    generar_magic_link,
    generar_magic_link_info,
    obtener_magic_link,
    subir_archivo_idonia,
    subir_estudio_idonia,
    validar_whoami_idonia,
)
from services.recog_service import humanizar_con_recog, humanizar_con_recog_pdf_buffer
from services.service_errors import ServiceError
from src.application.use_cases.orchestrate_patient_transfer import (
    build_pat002_clinical_identity,
    orchestrate_pat002_clinical_staging_flow,
    read_required_phase1_report_bytes,
    read_required_study_bytes,
)
from src.infrastructure.http.idonia_adapter import IdoniaHttpGateway
from src.infrastructure.http.recog_adapter import RecogHttpGateway

router = APIRouter()
_IDONIA_ACCESS_CACHE: dict[str, dict] = {}
settings = get_settings()
_idonia_gateway = IdoniaHttpGateway()
_recog_gateway = RecogHttpGateway()


def _mask_presence(value: str) -> dict:
    return {
        "configured": bool(value and value.strip()),
        "length": len(value.strip()) if value else 0,
    }


def _build_humanized_response(patient_text: str) -> HumanizedReport:
    findings = [line.strip("- ").strip() for line in patient_text.split("\n") if line.strip()][:3]
    return HumanizedReport(
        patient_summary=patient_text,
        complexity="medium",
        key_findings=findings,
        recommended_actions="Sigue las indicaciones de tu medico y consulta urgencias si presentas empeoramiento.",
    )


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text_to_pdf_bytes(text: str) -> bytes:
    wrapped = textwrap.wrap(text, width=90)[:45] or ["No hay contenido disponible"]

    stream_lines = ["BT", "/F1 10 Tf", "50 780 Td"]
    for i, line in enumerate(wrapped):
        if i > 0:
            stream_lines.append("0 -14 Td")
        stream_lines.append(f"({_escape_pdf_text(line)}) Tj")
    stream_lines.append("ET")

    stream = "\n".join(stream_lines).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
    )
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(f"5 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream\nendobj\n")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def _build_study_summary_text(patient_name: str) -> str:
    return (
        f"Estudio radiologico de {patient_name}. "
        "Documento demo generado para visualizacion en Idonia durante el hackathon. "
        "Para validar imagen diagnostica real se requiere el DICOM original del centro medico."
    )


def _read_phase1_report_pdf_bytes() -> bytes:
    return read_required_phase1_report_bytes()


async def _build_humanized_patient_text(patient_name: str, report_text: str, specialty: str | None = None) -> str:
    humanized_text = await humanizar_con_recog(report_text, specialty)
    return (
        f"Informe para paciente: {patient_name}\n\n"
        f"{humanized_text}"
    )


async def _upload_full_bundle(
    *,
    patient_id: str,
    patient_name: str,
    sample_report: str,
    specialty: str | None,
    dicom_patient_id: str,
    dicom_accession_number: str,
    dicom_study_description: str,
) -> dict:
    patient_humanized_text = await _build_humanized_patient_text(patient_name, sample_report, specialty)

    # 1) Informe técnico Fase I en memoria.
    report_bytes = _read_phase1_report_pdf_bytes()
    report_filename = "Informe_RM_RODILLA.pdf"

    report_result = await subir_archivo_idonia(
        file_name=report_filename,
        file_content=report_bytes,
        content_type="application/pdf",
        dicom_patient_id=dicom_patient_id,
        dicom_accession_number=dicom_accession_number,
        dicom_study_description=dicom_study_description,
    )

    # 2) Informe humanizado para paciente en memoria.
    humanized_bytes = _text_to_pdf_bytes(patient_humanized_text)
    await subir_archivo_idonia(
        file_name=f"Informe_para_paciente_{patient_id}.pdf",
        file_content=humanized_bytes,
        content_type="application/pdf",
        dicom_patient_id=dicom_patient_id,
        dicom_accession_number=dicom_accession_number,
        dicom_study_description=dicom_study_description,
    )

    # 3) Estudio DICOM/adjunto: obligatorio y en memoria, sin fallback local.
    study_filename, study_bytes, study_content_type = _load_required_study_bytes()

    await subir_estudio_idonia(
        file_name=study_filename,
        file_content=study_bytes,
        content_type=study_content_type,
        dicom_patient_id=dicom_patient_id,
        dicom_accession_number=dicom_accession_number,
        dicom_study_description=dicom_study_description,
    )

    return report_result


def _build_pat002_clinical_identity_route(patient_id: str) -> tuple[str, str, str]:
    """
    Manual hackathon: PAT-002 debe resolverse obligatoriamente a Carolina/D210105597.
    Ruta clínica en Idonia: Traslados desde Asturias/<DNI>.
    """
    if patient_id != "PAT-002":
        raise ServiceError(
            "El circuito clinico real de staging solo aplica a PAT-002",
            status_code=400,
            code="clinical_flow_invalid_patient",
            details={"expected_patient_id": "PAT-002", "received": patient_id},
        )

    identity = build_pat002_clinical_identity()
    return identity.dicom_patient_id, identity.dicom_accession_number, identity.route


def _load_required_study_bytes() -> tuple[str, bytes, str]:
    return read_required_study_bytes()


def _raise_clinical_phase_error(*, phase: str, manual_step: str, route: str, exc: ServiceError) -> None:
    details = dict(exc.details or {})
    details.update(
        {
            "phase": phase,
            "manual_step": manual_step,
            "route": route,
            "actionable_diagnosis": (
                "Revise credenciales/permisos del tenant en Idonia y el modo API key-only en Recog"
            ),
        }
    )
    raise ServiceError(
        f"Fallo en {phase}: {exc.message}",
        status_code=exc.status_code,
        code=exc.code,
        details=details,
    ) from exc


async def _orchestrate_pat002_clinical_staging_flow() -> dict:
    result = await orchestrate_pat002_clinical_staging_flow(
        idonia_gateway=_idonia_gateway,
        recog_gateway=_recog_gateway,
        report_bytes_provider=_read_phase1_report_pdf_bytes,
        study_bytes_provider=_load_required_study_bytes,
    )

    patient = PATIENT_MAP.get("PAT-002")
    if not patient:
        raise ServiceError(
            "No se encontro PAT-002 en catalogo clinico",
            status_code=404,
            code="clinical_patient_not_found",
        )

    return {
        "patient": patient,
        "route": result.route,
        "report_upload": result.report_upload,
        "study_upload": result.study_upload,
        "humanized_upload": result.humanized_upload,
        "magic_link_url": result.magic_link_url,
        "magic_link_pin": result.magic_link_pin,
    }


def _select_magic_link_reference(
    upload_result: dict,
    *,
    dicom_patient_id: str,
    dicom_accession_number: str,
    dicom_study_description: str,
) -> str:
    mode = settings.idonia_magic_link_reference_mode.strip().lower()
    if mode == "route_folder":
        return f"{dicom_patient_id}/{dicom_accession_number}"
    if mode == "route_full":
        return f"{dicom_patient_id}/{dicom_accession_number}/{dicom_study_description}"

    # Modo compatible histórico: prioriza file_id y si no existe usa route.
    return str(upload_result.get("file_id") or upload_result["route"]).lstrip("/")


async def _run_pipeline(request: ProcessReportRequest) -> tuple[HumanizedReport, dict, dict, str]:
    humanized_payload: HumanizedReport
    patient_text: str

    try:
        fhir_fields = await extract_fhir_fields(request.dictation_report)
    except ServiceError:
        raise
    except Exception as exc:
        raise ServiceError(
            "Error en pipeline de IA para FHIR",
            code="pipeline_llm_error",
            details={"reason": str(exc)},
        ) from exc

    try:
        patient_text = await humanizar_con_recog(request.dictation_report, request.specialty)
        humanized_payload = _build_humanized_response(patient_text)
    except ServiceError as recog_exc:
        # Fallback de continuidad clínica: si Recog falla por cuota/red, usar humanización local/LLM.
        try:
            fallback_humanized = await humanize_report(request.dictation_report, request.specialty)
            patient_text = fallback_humanized.patient_summary
            humanized_payload = fallback_humanized
        except Exception as fallback_exc:
            raise ServiceError(
                "Error en pipeline de IA para humanizacion",
                code="pipeline_humanization_error",
                details={
                    "recog_reason": str(recog_exc),
                    "fallback_reason": str(fallback_exc),
                },
            ) from fallback_exc
    except Exception as exc:
        raise ServiceError(
            "Error en pipeline de IA para humanizacion",
            code="pipeline_humanization_error",
            details={"reason": str(exc)},
        ) from exc

    upload_file_name = f"informe_{uuid.uuid4().hex[:8]}.pdf"
    upload_content = _text_to_pdf_bytes(patient_text)

    # Validar y derivar parámetros DICOM requeridos por manual de Idonia
    patient = PATIENT_MAP.get(request.patient_id or "") if request.patient_id else None
    dicom_patient_id = request.dicom_patient_id or "Traslados desde Asturias"
    dicom_accession_number = request.dicom_accession_number or (patient.dni if patient else None) or request.patient_id or f"ACC-{uuid.uuid4().hex[:8].upper()}"
    dicom_study_description = request.dicom_study_description or "RM_Rodilla"

    # Intentar subir a Idonia; si falla (credenciales demo) continuar sin Magic Link
    upload_result: dict = {"route": None, "raw": {}}
    magic_link: str = ""
    try:
        upload_result = await subir_archivo_idonia(
            file_name=upload_file_name,
            file_content=upload_content,
            content_type="application/pdf",
            dicom_patient_id=dicom_patient_id,
            dicom_accession_number=dicom_accession_number,
            dicom_study_description=dicom_study_description,
        )
        # Construir referencia consistente con el modo configurado
        magic_link_reference = _select_magic_link_reference(
            upload_result,
            dicom_patient_id=dicom_patient_id,
            dicom_accession_number=dicom_accession_number,
            dicom_study_description=dicom_study_description,
        )
        magic_link = await generar_magic_link(magic_link_reference)
    except ServiceError:
        # Sin credenciales Idonia el informe sigue siendo válido (FHIR + humanización OK)
        upload_result = {"route": None, "raw": {}}
        magic_link = ""

    return humanized_payload, fhir_fields, upload_result, magic_link


@router.post("/process", response_model=ProcessedReportResponse)
async def process_report(request: ProcessReportRequest):
    try:
        humanized, fhir_fields, upload_result, magic_link = await _run_pipeline(request)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc

    patient_id = request.patient_id or f"DEMO-{uuid.uuid4().hex[:8].upper()}"
    fhir_resource = build_diagnostic_report(request.dictation_report, patient_id, fhir_fields)

    return ProcessedReportResponse(
        report_id=fhir_resource.id,
        original_text=request.dictation_report,
        humanized=humanized,
        fhir_resource=fhir_resource,
        idonia_pdf_generated=bool(upload_result.get("route")),
        created_at=datetime.now(timezone.utc),
    )


@router.post("/process/pdf")
async def process_pdf(request: ProcessReportRequest):
    try:
        patient_text = await humanizar_con_recog(request.dictation_report, request.specialty)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc

    pdf_bytes = _text_to_pdf_bytes(patient_text)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=informe-paciente.pdf"},
    )


@router.post("/patients/{patient_id}/idonia-link", response_model=IdoniaAccessResponse)
async def create_patient_idonia_link(
    patient_id: str,
    resource: Literal["report", "study"] = "report",
    expired_creation_mode: Literal["create", "skip", "update"] | None = Query(default=None),
    include_bundle: bool = Query(default=True),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    patient = PATIENT_MAP.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    expose_pin = current_user["role"] == UserRole.patient

    # Flujo clínico real del hackathon: sin fallback local para PAT-002.
    if patient_id == "PAT-002" and resource == "report":
        try:
            result = await _orchestrate_pat002_clinical_staging_flow()
        except ServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc

        access_id = uuid.uuid4().hex
        _IDONIA_ACCESS_CACHE[access_id] = {
            "url": result["magic_link_url"],
            "created_at": datetime.now(timezone.utc),
        }

        public_base_url = settings.idonia_magic_link_public_base_url.strip()
        return IdoniaAccessResponse(
            status="ok",
            file_id=str(result["humanized_upload"].get("file_id") or ""),
            open_path=f"/api/reports/idonia/open/{access_id}",
            resource="report",
            magic_link_url=result["magic_link_url"],
            magic_link_base_url=public_base_url or None,
            magic_link_route=result["route"],
            magic_link_route_urlsafe=quote(result["route"], safe=""),
            magic_link_pin=result["magic_link_pin"] if expose_pin else None,
            password_control={
                "algorithm": "IDONIA_AUTO_PIN",
                "hash_applied": False,
                "lopdgdd": (
                    "PIN devuelto por endpoint de Magic Link; distribuir solo por canal seguro"
                    if expose_pin
                    else "Acceso profesional gestionado por protocolo medico; PIN no expuesto en esta respuesta"
                ),
            },
            created_at=datetime.now(timezone.utc),
        )

    dicom_patient_id = "Traslados desde Asturias"
    dicom_accession_number = patient.dni
    dicom_study_description = "RM_Rodilla"
    magic_link_reference = f"{dicom_patient_id}/{dicom_accession_number}"

    try:
        if resource == "study":
            pdf_bytes = _text_to_pdf_bytes(_build_study_summary_text(patient.name))
            file_name = f"estudio_{patient_id.lower()}.pdf"
        else:
            pdf_bytes = _read_phase1_report_pdf_bytes()
            file_name = "Informe_RM_RODILLA.pdf"

        if include_bundle:
            upload_result = await _upload_full_bundle(
                patient_id=patient_id,
                patient_name=patient.name,
                sample_report=patient.sample_report,
                specialty=patient.specialty,
                dicom_patient_id=dicom_patient_id,
                dicom_accession_number=dicom_accession_number,
                dicom_study_description=dicom_study_description,
            )
        else:
            if resource == "study":
                upload_result = await subir_estudio_idonia(
                    file_name=file_name,
                    file_content=pdf_bytes,
                    content_type="application/pdf",
                    dicom_patient_id=dicom_patient_id,
                    dicom_accession_number=dicom_accession_number,
                    dicom_study_description=dicom_study_description,
                )
            else:
                upload_result = await subir_archivo_idonia(
                    file_name=file_name,
                    file_content=pdf_bytes,
                    content_type="application/pdf",
                    dicom_patient_id=dicom_patient_id,
                    dicom_accession_number=dicom_accession_number,
                    dicom_study_description=dicom_study_description,
                )

        # Fase III: el ML debe apuntar al contenedor general del estudio (carpeta), no a archivo individual.
        magic_link_info = await generar_magic_link_info(
            magic_link_reference,
            expired_creation_mode=expired_creation_mode,
        )
        magic_link = str(magic_link_info["url"])
    except ServiceError as exc:
        if expose_pin:
            # Fallback para flujo paciente: evita bloquear UI cuando Idonia externo está degradado.
            public_base_url = settings.idonia_magic_link_public_base_url.strip() or "https://demo.idonia.com/v/idoniahackaton"
            demo_magic_link = f"{public_base_url}?url={quote(magic_link_reference, safe='')}"
            demo_pin = settings.idonia_magic_link_pin.strip() or None

            access_id = uuid.uuid4().hex
            _IDONIA_ACCESS_CACHE[access_id] = {
                "url": demo_magic_link,
                "created_at": datetime.now(timezone.utc),
            }

            return IdoniaAccessResponse(
                status="ok",
                file_id="",
                open_path=f"/api/reports/idonia/open/{access_id}",
                resource=resource,
                magic_link_url=demo_magic_link,
                magic_link_base_url=public_base_url,
                magic_link_route=magic_link_reference,
                magic_link_route_urlsafe=quote(magic_link_reference, safe=""),
                magic_link_pin=demo_pin,
                password_control={
                    "algorithm": "IDONIA_AUTO_PIN",
                    "hash_applied": False,
                    "lopdgdd": (
                        "Acceso devuelto en modo continuidad demo por indisponibilidad temporal del proveedor externo. "
                        "Comparte PIN por canal seguro y valida con soporte de Idonia si persiste."
                    ),
                },
                created_at=datetime.now(timezone.utc),
            )

        raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc

    access_id = uuid.uuid4().hex
    _IDONIA_ACCESS_CACHE[access_id] = {
        "url": magic_link,
        "created_at": datetime.now(timezone.utc),
    }

    public_base_url = settings.idonia_magic_link_public_base_url.strip()

    return IdoniaAccessResponse(
        status="ok",
        file_id=str(upload_result.get("file_id") or ""),
        open_path=f"/api/reports/idonia/open/{access_id}",
        resource=resource,
        magic_link_url=magic_link,
        magic_link_base_url=public_base_url or None,
        magic_link_route=magic_link_reference,
        magic_link_route_urlsafe=quote(magic_link_reference, safe=""),
        magic_link_pin=magic_link_info.get("pin") if expose_pin else None,
        password_control={
            "algorithm": "IDONIA_AUTO_PIN",
            "hash_applied": False,
            "lopdgdd": (
                "PIN devuelto por el endpoint de creacion del Magic Link; no compartir por canal inseguro"
                if expose_pin
                else "Acceso profesional gestionado por protocolo medico; PIN no expuesto en esta respuesta"
            ),
        },
        created_at=datetime.now(timezone.utc),
    )


@router.get("/idonia/open/{access_id}")
async def open_idonia(access_id: str):
    entry = _IDONIA_ACCESS_CACHE.get(access_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Acceso de Idonia expirado o no encontrado")

    _IDONIA_ACCESS_CACHE.pop(access_id, None)
    return RedirectResponse(url=str(entry["url"]))


@router.get("/idonia/file")
async def download_idonia_file(route: str = Query(..., min_length=1)):
    try:
        content = await descargar_archivo_idonia(route)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc

    return Response(content=content, media_type="application/octet-stream")


@router.get("/idonia/whoami")
async def idonia_whoami():
    try:
        payload = await validar_whoami_idonia()
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc

    return {
        "status": "ok",
        "whoami": payload,
    }


@router.get("/idonia/magic-link")
async def idonia_get_magic_link(
    route: str = Query(..., min_length=1),
    return_expired: bool = Query(default=False),
):
    try:
        payload = await obtener_magic_link(
            route,
            return_expired=return_expired,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc

    return {
        "status": "ok",
        **payload,
    }


@router.get("/integration/diagnostics")
async def integration_diagnostics(
    route: str = Query(default="Traslados desde Asturias/D210105597", min_length=1),
):
    """
    Diagnóstico unificado del flujo hackathon:
    - Estado de configuración de Recog e Idonia
    - Conectividad Idonia whoami
    - Consulta GET de Magic Link sobre una ruta (sin efectos de escritura)
    """
    recog_config = {
        "api_url": _mask_presence(settings.recog_api_url),
        "api_key": _mask_presence(settings.recog_api_key),
        "auth_mode": settings.recog_auth_mode,
        "auth_base_url": settings.recog_auth_base_url,
        "client_id": _mask_presence(settings.recog_client_id),
        "client_secret": _mask_presence(settings.recog_client_secret),
        "strict_mode": settings.recog_strict_mode,
        "ready": bool(
            settings.recog_api_url and (
                (settings.recog_client_id and settings.recog_client_secret)
                or settings.recog_api_key
            )
        ),
    }

    idonia_config = {
        "base_url": settings.idonia_base_url,
        "public_id": _mask_presence(settings.idonia_public_id),
        "api_secret": _mask_presence(settings.idonia_api_secret),
        "api_key_compound": _mask_presence(settings.idonia_api_key),
        "magic_link": {
            "path": settings.idonia_magic_link_path,
            "query_param": settings.idonia_magic_link_query_param,
            "public_base_url": settings.idonia_magic_link_public_base_url,
            "reference_mode": settings.idonia_magic_link_reference_mode,
        },
    }

    whoami_result: dict = {
        "ok": False,
        "error": None,
    }
    try:
        whoami_payload = await validar_whoami_idonia()
        whoami_result = {
            "ok": True,
            "keys": list(whoami_payload.keys()) if isinstance(whoami_payload, dict) else [],
            "error": None,
        }
    except ServiceError as exc:
        whoami_result = {
            "ok": False,
            "error": {
                "code": exc.code,
                "status_code": exc.status_code,
                "message": exc.message,
                "details": exc.details,
            },
        }

    magic_link_lookup: dict = {
        "ok": False,
        "route": route,
        "status_code": None,
        "url": None,
        "pin": None,
        "is_expired": None,
        "error": None,
    }
    try:
        lookup = await obtener_magic_link(route, return_expired=True)
        magic_link_lookup = {
            "ok": True,
            "route": route,
            "status_code": lookup.get("status_code"),
            "url": lookup.get("url"),
            "pin": lookup.get("pin"),
            "is_expired": lookup.get("is_expired"),
            "error": None,
        }
    except ServiceError as exc:
        magic_link_lookup = {
            "ok": False,
            "route": route,
            "status_code": exc.status_code,
            "url": None,
            "pin": None,
            "is_expired": None,
            "error": {
                "code": exc.code,
                "status_code": exc.status_code,
                "message": exc.message,
                "details": exc.details,
            },
        }

    overall_status = "ok"
    blockers: list[str] = []
    if not recog_config["ready"] and recog_config["strict_mode"]:
        overall_status = "blocked"
        blockers.append("recog_not_configured")
    if not whoami_result["ok"]:
        overall_status = "blocked"
        blockers.append("idonia_whoami_failed")

    return {
        "status": overall_status,
        "blockers": blockers,
        "recog": recog_config,
        "idonia": {
            "config": idonia_config,
            "whoami": whoami_result,
            "magic_link_lookup": magic_link_lookup,
        },
    }
