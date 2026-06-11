import io
import httpx
import time
from pypdf import PdfReader

from config import get_settings
from services.service_errors import ServiceError

settings = get_settings()
_RECOG_TOKEN_CACHE: dict[str, object] = {
    "access_token": "",
    "expires_at": 0,
}


def _resolve_recog_auth_mode() -> str:
    mode = (settings.recog_auth_mode or "auto").strip().lower()
    if mode in {"oauth", "oauth2", "client_credentials"}:
        return "oauth"
    if mode in {"api_key", "apikey", "x-api-key"}:
        return "api_key"
    return "auto"


def _is_oauth_configured() -> bool:
    return bool(settings.recog_client_id and settings.recog_client_secret)


def _is_api_key_configured() -> bool:
    return bool(settings.recog_api_key)


def _is_recog_configured() -> bool:
    """Devuelve True si hay URL y mecanismo de auth válido (OAuth o API key)."""
    if not settings.recog_api_url:
        return False

    mode = _resolve_recog_auth_mode()
    if mode == "oauth":
        return _is_oauth_configured()
    if mode == "api_key":
        return _is_api_key_configured()

    # auto: prioriza OAuth si está disponible; si no, API key.
    return _is_oauth_configured() or _is_api_key_configured()


async def _get_recog_oauth_token() -> str:
    cached_token = str(_RECOG_TOKEN_CACHE.get("access_token") or "")
    cached_expiry = int(_RECOG_TOKEN_CACHE.get("expires_at") or 0)
    now = int(time.time())
    # Renovación proactiva 60s antes de expirar
    if cached_token and cached_expiry - 60 > now:
        return cached_token

    if not _is_oauth_configured():
        raise ServiceError(
            "Recog OAuth no configurado (faltan RECOG_CLIENT_ID/RECOG_CLIENT_SECRET)",
            status_code=503,
            code="recog_oauth_not_configured",
        )

    token_url = f"{settings.recog_auth_base_url.rstrip('/')}/oauth/token"
    form_data = {
        "grant_type": "client_credentials",
        "client_id": settings.recog_client_id,
        "client_secret": settings.recog_client_secret,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.integration_timeout_seconds) as client:
            response = await client.post(
                token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=form_data,
            )
    except httpx.HTTPError as exc:
        raise ServiceError(
            "No se pudo obtener token OAuth de Recog",
            status_code=502,
            code="recog_oauth_connection_error",
            details={"reason": str(exc)},
        ) from exc

    if response.status_code >= 400:
        raise ServiceError(
            "Recog rechazo la obtencion del token OAuth",
            status_code=502,
            code="recog_oauth_http_error",
            details={
                "status_code": response.status_code,
                "response": response.text[:500],
            },
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise ServiceError(
            "Respuesta no JSON al obtener token OAuth de Recog",
            status_code=502,
            code="recog_oauth_invalid_json",
            details={"response": response.text[:500]},
        ) from exc

    access_token = str(payload.get("access_token") or "").strip()
    expires_in = int(payload.get("expires_in") or 3600)
    if not access_token:
        raise ServiceError(
            "Recog no devolvio access_token en OAuth",
            status_code=502,
            code="recog_oauth_missing_token",
        )

    _RECOG_TOKEN_CACHE["access_token"] = access_token
    _RECOG_TOKEN_CACHE["expires_at"] = now + max(expires_in, 60)
    return access_token


async def _build_recog_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    mode = _resolve_recog_auth_mode()

    if mode == "oauth":
        token = await _get_recog_oauth_token()
        headers["Authorization"] = f"Bearer {token}"
        return headers

    if mode == "api_key":
        if not settings.recog_api_key:
            raise ServiceError(
                "Recog API key no configurada",
                status_code=503,
                code="recog_api_key_not_configured",
            )
        headers["X-API-Key"] = settings.recog_api_key
        return headers

    # auto: primero OAuth, si no hay creds OAuth usa API key
    if _is_oauth_configured():
        token = await _get_recog_oauth_token()
        headers["Authorization"] = f"Bearer {token}"
        return headers

    if settings.recog_api_key:
        headers["X-API-Key"] = settings.recog_api_key
        return headers

    raise ServiceError(
        "Recog no esta configurado (falta OAuth o API key)",
        status_code=503,
        code="recog_not_configured",
    )


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


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        raise ServiceError(
            "No se pudo abrir el PDF devuelto por Recog",
            status_code=502,
            code="recog_pdf_open_error",
            details={"reason": str(exc)},
        ) from exc

    pages_text: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text.strip():
            pages_text.append(page_text.strip())

    extracted = "\n\n".join(pages_text).strip()
    if extracted:
        return extracted

    raise ServiceError(
        "Recog devolvio un PDF sin texto extraible",
        status_code=502,
        code="recog_pdf_empty_text",
    )


async def humanizar_con_recog(dictation_report: str, specialty: str | None = None) -> str:
    """
    Humaniza el informe médico con la API de Recog.
    En modo estricto (por defecto), falla si Recog no está configurado o no responde.
    En modo no estricto, usa fallback demo del servicio LLM.
    """
    if not _is_recog_configured():
        if settings.recog_strict_mode:
            raise ServiceError(
                "Recog no esta configurado (faltan RECOG_API_URL/RECOG_API_KEY)",
                status_code=503,
                code="recog_not_configured",
            )

        # Fallback: usar el generador demo del servicio LLM (no requiere credenciales)
        from services.azure_llm_service import _demo_humanize_report
        humanized = _demo_humanize_report(dictation_report)
        return humanized.patient_summary

    body = {"dictationReport": dictation_report}
    if specialty:
        body["specialty"] = specialty

    headers = await _build_recog_headers()

    try:
        async with httpx.AsyncClient(timeout=settings.integration_timeout_seconds) as client:
            response = await client.post(settings.recog_api_url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        if settings.recog_strict_mode:
            raise ServiceError(
                "No se pudo conectar con Recog",
                status_code=502,
                code="recog_connection_error",
                details={"reason": str(exc)},
            ) from exc

        # Modo no estricto: usar fallback demo en lugar de propagar error
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

    content_type = (response.headers.get("content-type") or "").lower()
    if "application/pdf" in content_type:
        return _extract_text_from_pdf_bytes(response.content)

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    return _extract_humanized_text(payload, response.text)
