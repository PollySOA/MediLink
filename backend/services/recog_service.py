import httpx

from config import get_settings
from services.service_errors import ServiceError

settings = get_settings()


def _is_recog_configured() -> bool:
    """Devuelve True sólo si tenemos tanto URL como API key de Recog configurados."""
    return bool(settings.recog_api_url and settings.recog_api_key)


def _extract_humanized_text(payload: dict, fallback_text: str) -> str:
    candidates = [
        payload.get("patientText"),
        payload.get("patient_text"),
        payload.get("humanizedText"),
        payload.get("humanized_text"),
        payload.get("summary"),
        payload.get("text"),
        payload.get("result"),
    ]
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()

    if fallback_text.strip():
        return fallback_text.strip()

    raise ServiceError(
        "Recog no devolvio texto humanizado utilizable",
        code="recog_empty_payload",
        details={"payload_keys": list(payload.keys())},
    )


async def humanizar_con_recog(dictation_report: str, specialty: str | None = None) -> str:
    """
    Humaniza el informe médico con la API de Recog.
    Si Recog no está configurado o falla, usa el fallback demo del servicio LLM.
    """
    if not _is_recog_configured():
        # Fallback: usar el generador demo del servicio LLM (no requiere credenciales)
        from services.azure_llm_service import _demo_humanize_report
        humanized = _demo_humanize_report(dictation_report)
        return humanized.patient_summary

    body = {"dictationReport": dictation_report}
    if specialty:
        body["specialty"] = specialty

    headers = {"Content-Type": "application/json"}
    if settings.recog_api_key:
        headers["X-API-Key"] = settings.recog_api_key

    try:
        async with httpx.AsyncClient(timeout=settings.integration_timeout_seconds) as client:
            response = await client.post(settings.recog_api_url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        # Red caída: usar fallback demo en lugar de propagar error
        from services.azure_llm_service import _demo_humanize_report
        humanized = _demo_humanize_report(dictation_report)
        return humanized.patient_summary

    if response.status_code >= 400:
        raise ServiceError(
            "Recog rechazo la solicitud de humanizacion",
            status_code=502,
            code="recog_http_error",
            details={
                "status_code": response.status_code,
                "response": response.text[:500],
            },
        )

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    return _extract_humanized_text(payload, response.text)
