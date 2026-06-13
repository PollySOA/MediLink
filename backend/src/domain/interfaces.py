from typing import Protocol


class IdoniaGateway(Protocol):
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
        ...

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
        ...

    async def get_magic_link(self, route: str, return_expired: bool = True) -> dict:
        ...

    async def create_magic_link(self, route: str, return_expired: bool = True) -> dict:
        ...


class RecogGateway(Protocol):
    async def humanize_report_pdf(self, dictation_report: str, specialty: str | None = None) -> bytes:
        ...
