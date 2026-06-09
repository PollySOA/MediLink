from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, status

from config import get_settings
from models.schemas import PacienteDemo
from services.idonia_service import generar_magic_link_info, subir_archivo_idonia, subir_estudio_idonia
from services.service_errors import ServiceError

router = APIRouter()
settings = get_settings()

PACIENTES_DB: dict[str, PacienteDemo] = {
    "D210105597": PacienteDemo(
        nombre="Carolina Riera Segura",
        dni="D210105597",
        especialidad="Traumatología",
        diagnostico_corto="Lesión de rodilla - Picos de Europa",
    )
}


def _pdf_fase1_path() -> Path:
    return Path(__file__).resolve().parents[1] / "static" / "ficheros_reto" / "Informe_RM_RODILLA.pdf"


@router.post("/ingesta/{patient_dni}", status_code=status.HTTP_201_CREATED)
async def ejecutar_fase_i_y_ii(patient_dni: str):
    paciente = PACIENTES_DB.get(patient_dni)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado en el dataset demo")

    pdf_path = _pdf_fase1_path()
    if not pdf_path.is_file():
        raise HTTPException(
            status_code=500,
            detail="Fichero real Informe_RM_RODILLA.pdf no encontrado en el servidor",
        )

    file_content = pdf_path.read_bytes()

    dicom_patient_id = "Traslados desde Asturias"
    dicom_accession_number = paciente.dni
    dicom_study_description = "RM_Rodilla"

    try:
        await subir_archivo_idonia(
            file_name="Informe_RM_RODILLA.pdf",
            file_content=file_content,
            content_type="application/pdf",
            dicom_patient_id=dicom_patient_id,
            dicom_accession_number=dicom_accession_number,
            dicom_study_description=dicom_study_description,
        )
        # Mantiene el contenedor con prueba de estudio para Fase III
        await subir_estudio_idonia(
            file_name="RM_Rodilla_Referencia.pdf",
            file_content=file_content,
            content_type="application/pdf",
            dicom_patient_id=dicom_patient_id,
            dicom_accession_number=dicom_accession_number,
            dicom_study_description=dicom_study_description,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc

    return {
        "status": "success",
        "message": "Fase I completada. Archivo real de Carolina Riera Segura ingresado en Idonia.",
        "estructura_carpeta": f"{dicom_patient_id} / {dicom_accession_number}",
    }


@router.post("/magic-link/{patient_dni}")
async def generar_magic_link_agrupado(patient_dni: str):
    paciente = PACIENTES_DB.get(patient_dni)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente inválido")

    ruta_carpeta_clinica = f"Traslados desde Asturias/{paciente.dni}"
    ruta_url_safe = quote(ruta_carpeta_clinica, safe="")

    try:
        magic_link_info = await generar_magic_link_info(
            ruta_carpeta_clinica,
            query_param_override="route",
            expired_creation_mode="create",
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_http_detail()) from exc

    magic_link_url = str(magic_link_info["url"])

    visor_url = settings.idonia_magic_link_public_base_url or "https://staging.idonia.com/v/hacknum23"
    if not str(magic_link_url).startswith("http"):
        magic_link_url = f"{visor_url}?url={ruta_url_safe}"

    return {
        "status": "Magic Link Generado Exitosamente",
        "visor_url": visor_url,
        "magic_link_url": magic_link_url,
        "query_param": "route",
        "route": ruta_carpeta_clinica,
        "route_urlsafe": ruta_url_safe,
        "PIN": magic_link_info.get("pin"),
        "password_control": {
            "source": "idonia_magic_link_endpoint",
            "lopdgdd": "El acceso usa el PIN devuelto por Idonia al crear el Magic Link; no compartirlo por canal inseguro.",
        },
        "documentos_incluidos": [
            "RM_Rodilla (estudio)",
            "Informe_RM_RODILLA.pdf (Original)",
            "Informe humanizado para paciente",
        ],
    }
