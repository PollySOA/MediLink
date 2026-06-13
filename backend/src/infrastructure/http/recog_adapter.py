from src.domain.interfaces import RecogGateway
from services.recog_service import humanizar_con_recog_pdf_buffer


class RecogHttpGateway(RecogGateway):
    async def humanize_report_pdf(self, dictation_report: str, specialty: str | None = None) -> bytes:
        return await humanizar_con_recog_pdf_buffer(dictation_report, specialty=specialty)
