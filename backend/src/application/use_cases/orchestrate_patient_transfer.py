import io
from pathlib import Path

from data.fictional_patients import PATIENT_MAP
from services.service_errors import ServiceError
from src.domain.entities import ClinicalIdentity, ClinicalOrchestrationResult
from src.domain.interfaces import IdoniaGateway, RecogGateway
from src.infrastructure.config.settings import get_settings


def build_pat002_clinical_identity() -> ClinicalIdentity:
    patient = PATIENT_MAP.get("PAT-002")
    if not patient:
        raise ServiceError(
            "No se encontro el paciente PAT-002 en el catalogo clinico",
            status_code=404,
            code="clinical_patient_not_found",
        )

    dni = "D210105597"
    if patient.dni != dni:
        raise ServiceError(
            "DNI clinico de PAT-002 no coincide con el esperado por manual",
            status_code=500,
            code="clinical_identity_mismatch",
            details={"catalog_dni": patient.dni, "expected_dni": dni},
        )

    dicom_patient_id = "Traslados desde Asturias"
    return ClinicalIdentity(
        patient_id="PAT-002",
        dicom_patient_id=dicom_patient_id,
        dicom_accession_number=dni,
        dicom_study_description="RM_Rodilla",
        route=f"{dicom_patient_id}/{dni}",
    )


def read_required_phase1_report_bytes() -> bytes:
    report_path = Path("static/ficheros_reto/Informe_RM_RODILLA.pdf")
    if not report_path.is_file():
        raise ServiceError(
            "No se encontró el fichero requerido para Fase I: static/ficheros_reto/Informe_RM_RODILLA.pdf",
            status_code=500,
            code="phase1_report_file_missing",
        )
    return io.BytesIO(report_path.read_bytes()).getvalue()


def read_required_study_bytes() -> tuple[str, bytes, str]:
    settings = get_settings()
    raw_path = settings.idonia_source_study_file_path.strip()
    if not raw_path:
        raise ServiceError(
            "Falta IDONIA_SOURCE_STUDY_FILE_PATH para flujo real de staging",
            status_code=500,
            code="study_source_missing",
        )

    source_path = Path(raw_path)
    if not source_path.is_file():
        raise ServiceError(
            "No se encontro el estudio de imagen requerido para staging",
            status_code=500,
            code="study_source_not_found",
            details={"path": raw_path},
        )

    file_name = source_path.name
    content_type = "application/dicom" if file_name.lower().endswith(".dcm") else "application/octet-stream"
    return file_name, io.BytesIO(source_path.read_bytes()).getvalue(), content_type


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


async def orchestrate_pat002_clinical_staging_flow(
    *,
    idonia_gateway: IdoniaGateway,
    recog_gateway: RecogGateway,
    report_bytes_provider=read_required_phase1_report_bytes,
    study_bytes_provider=read_required_study_bytes,
) -> ClinicalOrchestrationResult:
    identity = build_pat002_clinical_identity()

    # Fast-path operativo: si ya existe un Magic Link válido para la ruta clínica,
    # reutilizarlo para no reconsumir cuota de Recog en cada apertura de UI.
    try:
        existing_magic_link = await idonia_gateway.get_magic_link(identity.route, return_expired=True)
        existing_url = str(existing_magic_link.get("url") or "")
        existing_pin = existing_magic_link.get("pin")
        is_expired = bool(existing_magic_link.get("is_expired", False))

        if existing_url and not is_expired:
            # Refresca PIN/URL sin pasar por Recog para evitar desincronizaciones de acceso en UI.
            try:
                refreshed_magic_link = await idonia_gateway.create_magic_link(identity.route, return_expired=True)
                refreshed_url = str(refreshed_magic_link.get("url") or "")
                refreshed_pin = refreshed_magic_link.get("pin")
                if refreshed_url:
                    existing_url = refreshed_url
                if refreshed_pin:
                    existing_pin = refreshed_pin
            except ServiceError:
                # Si falla el refresh, se mantiene la mejor referencia válida ya consultada.
                pass

            return ClinicalOrchestrationResult(
                route=identity.route,
                report_upload={"route": identity.route, "file_id": "reused", "raw": {"reused": True}},
                study_upload={"route": identity.route, "file_id": "reused", "raw": {"reused": True}},
                humanized_upload={"route": identity.route, "file_id": "reused", "raw": {"reused": True}},
                magic_link_url=existing_url,
                magic_link_pin=existing_pin,
            )
    except ServiceError:
        # Si no existe todavía el Magic Link o la lookup falla, continuar con el flujo completo.
        pass

    try:
        report_upload = await idonia_gateway.upload_report(
            file_name="Informe_RM_RODILLA.pdf",
            file_content=report_bytes_provider(),
            content_type="application/pdf",
            dicom_patient_id=identity.dicom_patient_id,
            dicom_accession_number=identity.dicom_accession_number,
            dicom_study_description=identity.dicom_study_description,
        )

        study_file_name, study_bytes, study_content_type = study_bytes_provider()
        study_upload = await idonia_gateway.upload_study(
            file_name=study_file_name,
            file_content=study_bytes,
            content_type=study_content_type,
            dicom_patient_id=identity.dicom_patient_id,
            dicom_accession_number=identity.dicom_accession_number,
            dicom_study_description=identity.dicom_study_description,
        )
    except ServiceError as exc:
        _raise_clinical_phase_error(
            phase="Fase I - Ingesta e interoperabilidad en Idonia",
            manual_step="2",
            route=identity.route,
            exc=exc,
        )

    clinical_findings = (
        "gonalgia derecha. Articulacion femoropatelar con patela alta "
        "(indice IS de 1,5) con fisuras grado II-III en faceta patelar externa."
    )

    try:
        humanized_pdf_buffer = await recog_gateway.humanize_report_pdf(clinical_findings, specialty="Radiologia")
    except ServiceError as exc:
        _raise_clinical_phase_error(
            phase="Fase II - Humanizacion con Recog",
            manual_step="3",
            route=identity.route,
            exc=exc,
        )

    try:
        humanized_upload = await idonia_gateway.upload_report(
            file_name="Informe para paciente.pdf",
            file_content=humanized_pdf_buffer,
            content_type="application/pdf",
            dicom_patient_id=identity.dicom_patient_id,
            dicom_accession_number=identity.dicom_accession_number,
            dicom_study_description=identity.dicom_study_description,
        )

        magic_link_lookup = await idonia_gateway.get_magic_link(identity.route, return_expired=True)
        magic_link_url = str(magic_link_lookup.get("url") or "")
        magic_link_pin = magic_link_lookup.get("pin")

        if not magic_link_url:
            created = await idonia_gateway.create_magic_link(identity.route, return_expired=True)
            magic_link_url = str(created.get("url") or "")
            magic_link_pin = created.get("pin") or magic_link_pin

        if not magic_link_url:
            raise ServiceError(
                "No se pudo obtener ni crear el Magic Link clinico para la ruta del paciente",
                code="idonia_magic_link_missing",
                details={"route": identity.route},
            )
    except ServiceError as exc:
        _raise_clinical_phase_error(
            phase="Fase III - Entrega y Magic Link",
            manual_step="4",
            route=identity.route,
            exc=exc,
        )

    return ClinicalOrchestrationResult(
        route=identity.route,
        report_upload=report_upload,
        study_upload=study_upload,
        humanized_upload=humanized_upload,
        magic_link_url=magic_link_url,
        magic_link_pin=magic_link_pin,
    )
