from src.domain.interfaces import IdoniaGateway
from services.idonia_service import (
    generar_magic_link_info,
    obtener_magic_link,
    subir_archivo_idonia,
    subir_estudio_idonia,
)


class IdoniaHttpGateway(IdoniaGateway):
    async def upload_report(
        self,
        *,
        file_name: str,
        file_content: bytes,
        content_type: str,
        dicom_patient_id: str,
        dicom_accession_number: str,
        dicom_study_description: str,
    ) -> dict:
        return await subir_archivo_idonia(
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
            dicom_patient_id=dicom_patient_id,
            dicom_accession_number=dicom_accession_number,
            dicom_study_description=dicom_study_description,
        )

    async def upload_study(
        self,
        *,
        file_name: str,
        file_content: bytes,
        content_type: str,
        dicom_patient_id: str,
        dicom_accession_number: str,
        dicom_study_description: str,
    ) -> dict:
        return await subir_estudio_idonia(
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
            dicom_patient_id=dicom_patient_id,
            dicom_accession_number=dicom_accession_number,
            dicom_study_description=dicom_study_description,
        )

    async def get_magic_link(self, route: str, return_expired: bool = True) -> dict:
        return await obtener_magic_link(route, return_expired=return_expired)

    async def create_magic_link(self, route: str, return_expired: bool = True) -> dict:
        return await generar_magic_link_info(
            route,
            expired_creation_mode="create",
            return_expired=return_expired,
        )
