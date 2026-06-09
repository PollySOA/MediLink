import asyncio
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, Response

from config import get_settings
from data.fictional_patients import PATIENT_MAP
from models.schemas import HumanizedReport, ProcessReportRequest, ProcessedReportResponse
from models.schemas import IdoniaAccessResponse
from services.azure_llm_service import extract_fhir_fields
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
from services.recog_service import humanizar_con_recog
from services.service_errors import ServiceError

router = APIRouter()
_IDONIA_ACCESS_CACHE: dict[str, dict] = {}
settings = get_settings()


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
    try:
        with open("static/ficheros_reto/Informe_RM_RODILLA.pdf", "rb") as file_handle:
            return file_handle.read()
    except FileNotFoundError as exc:
        raise ServiceError(
            "No se encontró el fichero requerido para Fase I: static/ficheros_reto/Informe_RM_RODILLA.pdf",
            status_code=500,
            code="phase1_report_file_missing",
        ) from exc


def _load_optional_file_bytes(path_value: str) -> bytes | None:
    path = path_value.strip()
    if not path:
        return None

    candidate = Path(path)
    if not candidate.is_file():
        return None

    return candidate.read_bytes()


def _persist_humanized_text_file(*, patient_id: str, patient_name: str, content: str) -> Path:
    base_dir = Path("static/ficheros_reto/humanizados")
    base_dir.mkdir(parents=True, exist_ok=True)
    output_path = base_dir / f"Informe_para_paciente_{patient_id}.txt"
    output_path.write_text(content.strip() + "\n", encoding="utf-8")
    return output_path


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
    # 0) Crear siempre archivo humanizado local para trazabilidad de Fase II.
    patient_humanized_text = await _build_humanized_patient_text(patient_name, sample_report, specialty)
    _persist_humanized_text_file(
        patient_id=patient_id,
        patient_name=patient_name,
        content=patient_humanized_text,
    )

    # 1) Informe técnico Fase I: obligatorio cargar el PDF real entregado por el reto.
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

    # 2) Informe humanizado para paciente.
    humanized_bytes = _text_to_pdf_bytes(patient_humanized_text)
    await subir_archivo_idonia(
        file_name=f"Informe_para_paciente_{patient_id}.pdf",
        file_content=humanized_bytes,
        content_type="application/pdf",
        dicom_patient_id=dicom_patient_id,
        dicom_accession_number=dicom_accession_number,
        dicom_study_description=dicom_study_description,
    )

    # 3) Estudio DICOM/adjunto: usa fichero real si existe; fallback a resumen PDF.
    study_source_bytes = _load_optional_file_bytes(settings.idonia_source_study_file_path)
    if study_source_bytes:
        study_bytes = study_source_bytes
        study_filename = Path(settings.idonia_source_study_file_path).name or f"estudio_{patient_id.lower()}.dcm"
        lowered_name = study_filename.lower()
        study_content_type = "application/dicom" if lowered_name.endswith(".dcm") else "application/pdf"
    else:
        study_bytes = _text_to_pdf_bytes(_build_study_summary_text(patient_name))
        study_filename = f"estudio_{patient_id.lower()}.pdf"
        study_content_type = "application/pdf"

    await subir_estudio_idonia(
        file_name=study_filename,
        file_content=study_bytes,
        content_type=study_content_type,
        dicom_patient_id=dicom_patient_id,
        dicom_accession_number=dicom_accession_number,
        dicom_study_description=dicom_study_description,
    )

    return report_result


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
    try:
        patient_text, fhir_fields = await asyncio.gather(
            humanizar_con_recog(request.dictation_report, request.specialty),
            extract_fhir_fields(request.dictation_report),
        )
    except ServiceError:
        raise
    except Exception as exc:
        raise ServiceError(
            "Error en pipeline de IA para humanizacion/FHIR",
            code="pipeline_llm_error",
            details={"reason": str(exc)},
        ) from exc

    upload_file_name = f"informe_{uuid.uuid4().hex[:8]}.pdf"
    upload_content = _text_to_pdf_bytes(patient_text)

    # Intentar subir a Idonia; si falla (credenciales demo) continuar sin Magic Link
    upload_result: dict = {"route": None, "raw": {}}
    magic_link: str = ""
    try:
        upload_result = await subir_archivo_idonia(
            file_name=upload_file_name,
            file_content=upload_content,
            content_type="application/pdf",
        )
        magic_link = await generar_magic_link(upload_result.get("file_id") or upload_result["route"])
    except ServiceError:
        # Sin credenciales Idonia el informe sigue siendo válido (FHIR + humanización OK)
        upload_result = {"route": None, "raw": {}}
        magic_link = ""

    return _build_humanized_response(patient_text), fhir_fields, upload_result, magic_link


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
):
    patient = PATIENT_MAP.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    dicom_patient_id = "Traslados desde Asturias"
    dicom_accession_number = patient.dni
    dicom_study_description = "RM_Rodilla"

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
        magic_link_reference = f"{dicom_patient_id}/{dicom_accession_number}"
        magic_link_info = await generar_magic_link_info(
            magic_link_reference,
            expired_creation_mode=expired_creation_mode,
        )
        magic_link = str(magic_link_info["url"])
    except ServiceError as exc:
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
        magic_link_pin=magic_link_info.get("pin"),
        password_control={
            "algorithm": "IDONIA_AUTO_PIN",
            "hash_applied": False,
            "lopdgdd": "PIN devuelto por el endpoint de creacion del Magic Link; no compartir por canal inseguro",
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
