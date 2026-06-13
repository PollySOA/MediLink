import base64
import hashlib
import hmac
import json
import time
from urllib.parse import quote, urlencode

import httpx

from config import get_settings
from services.service_errors import ServiceError

settings = get_settings()


def _split_idonia_credentials() -> tuple[str, str]:
    raw = settings.idonia_api_key.strip()
    if raw:
        parts = raw.split("_")
        if len(parts) >= 3 and parts[-2] and parts[-1]:
            return parts[-2], parts[-1]

    public_id = settings.idonia_public_id.strip()
    signing_secret = settings.idonia_api_secret.strip()

    if public_id and signing_secret:
        if not public_id or not signing_secret:
            raise ServiceError(
                "No se pudo derivar public_id/secret para firmar JWT de Idonia",
                status_code=500,
                code="idonia_missing_jwt_parts",
            )

        return public_id, signing_secret

    if not raw:
        raise ServiceError(
            "No se encontraron credenciales de Idonia en las variables de entorno",
            status_code=500,
            code="idonia_missing_credentials",
        )

    parts = raw.split("_")
    if len(parts) < 3:
        raise ServiceError(
            "IDONIA_API_KEY no tiene formato valido. Se esperaba prefijo_publicId_secret",
            status_code=500,
            code="idonia_invalid_api_key_format",
        )

    public_id = parts[-2]
    signing_secret = parts[-1]

    if not public_id or not signing_secret:
        raise ServiceError(
            "No se pudo derivar public_id/secret para firmar JWT de Idonia",
            status_code=500,
            code="idonia_missing_jwt_parts",
        )

    return public_id, signing_secret


def _decode_idonia_secret(api_secret: str) -> bytes:
    raw = api_secret.strip()
    candidates = [raw]
    if raw.startswith("S2"):
        candidates.append(raw[2:])

    last_error: Exception | None = None
    for candidate in candidates:
        normalized = candidate.replace("-", "+").replace("_", "/")
        padding = "=" * (-len(normalized) % 4)
        try:
            return base64.b64decode(normalized + padding)
        except Exception as exc:  # pragma: no cover - ruta de compatibilidad defensiva
            last_error = exc

    raise ServiceError(
        "API secret de Idonia no valido para decodificacion URL-safe Base64",
        status_code=500,
        code="idonia_invalid_api_secret_format",
        details={"reason": str(last_error) if last_error else "unknown"},
    )


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def generar_jwt_idonia(public_id: str, api_secret: str) -> str:
    secret_bytes = _decode_idonia_secret(api_secret)
    now = int(time.time())

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": public_id,
        "iat": now - 300,
        "exp": now + 300,
    }

    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret_bytes, signing_input, hashlib.sha256).digest()

    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def calcular_password_hash_idonia(password: str) -> str:
    sha256_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return base64.b64encode(sha256_hex.encode("utf-8")).decode("ascii")


def _build_idonia_jwt() -> str:
    public_id, signing_secret = _split_idonia_credentials()
    return generar_jwt_idonia(public_id, signing_secret)


def _build_magic_link_payload(raw_payload: object) -> dict:
    payload = raw_payload
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            payload = first

    if not isinstance(payload, dict):
        return {}

    return payload


def _extract_magic_link_url(raw_payload: object) -> str | None:
    payload = _build_magic_link_payload(raw_payload)
    if not payload:
        return None

    link = (
        payload.get("magic_link")
        or payload.get("magicLink")
        or payload.get("url")
        or payload.get("URL")
        or payload.get("link")
    )
    if not link:
        return None

    return str(link)


def _upload_route(file_name: str) -> str:
    return settings.idonia_upload_template.format(num_participante=settings.idonia_num_participante) + f"/{file_name}"


def _studies_upload_route(file_name: str) -> str:
    return settings.idonia_studies_template.format(num_participante=settings.idonia_num_participante) + f"/{file_name}"


def _build_idonia_multipart_fields(
    *,
    dicom_patient_id: str | None,
    dicom_accession_number: str | None,
    dicom_study_description: str | None,
) -> dict[str, str]:
    data: dict[str, str] = {}
    if dicom_patient_id:
        data["DICOMPatientID"] = dicom_patient_id
    if dicom_accession_number:
        data["DICOMAccessionNumber"] = dicom_accession_number
    if dicom_study_description:
        data["DICOMStudyDescription"] = dicom_study_description
    return data


def _extract_uploaded_file_reference(payload: object, file_name: str) -> tuple[str, str]:
    if isinstance(payload, dict):
        candidate = payload.get("path") or payload.get("file") or payload.get("filePath") or payload.get("id")
        if candidate:
            candidate_value = str(candidate).lstrip("/")
            return candidate_value, candidate_value

        route = payload.get("route")
        if route:
            route_value = str(route).lstrip("/")
            return route_value, route_value

    if isinstance(payload, list) and payload:
        candidate_value = str(payload[0]).lstrip("/")
        return candidate_value, candidate_value

    fallback_route = _upload_route(file_name).lstrip("/")
    fallback_file_id = file_name
    return fallback_route, fallback_file_id


def _build_public_magic_link(file_reference: str) -> str:
    public_base_url = settings.idonia_magic_link_public_base_url.strip()
    encoded_reference = quote(file_reference, safe="")
    if public_base_url:
        # En whitelabels /v/<slug> el visor consume el valor mediante `url=...`.
        if "/v/" in public_base_url:
            separator = "&" if "?" in public_base_url else "?"
            return f"{public_base_url}{separator}url={encoded_reference}"

        separator = "&" if "?" in public_base_url else "?"
        return f"{public_base_url}{separator}{settings.idonia_magic_link_query_param}={encoded_reference}"

    magic_link_path = settings.idonia_magic_link_path.lstrip("/")
    return (
        f"{settings.idonia_base_url.rstrip('/')}/{magic_link_path}"
        f"?{settings.idonia_magic_link_query_param}={encoded_reference}"
    )


async def subir_archivo_idonia(
    *,
    file_name: str,
    file_content: bytes,
    content_type: str = "application/pdf",
    dicom_patient_id: str | None = None,
    dicom_accession_number: str | None = None,
    dicom_study_description: str | None = None,
) -> dict:
    upload_segment = settings.idonia_upload_template.format(num_participante=settings.idonia_num_participante)
    url = f"{settings.idonia_base_url.rstrip('/')}/files/{upload_segment}"

    headers = {
        "Authorization": f"Bearer {_build_idonia_jwt()}",
    }

    files = {
        "file": (file_name, file_content, content_type),
    }
    form_fields = _build_idonia_multipart_fields(
        dicom_patient_id=dicom_patient_id,
        dicom_accession_number=dicom_accession_number,
        dicom_study_description=dicom_study_description,
    )

    try:
        async with httpx.AsyncClient(timeout=settings.integration_timeout_seconds) as client:
            response = await client.post(url, headers=headers, files=files, data=form_fields)
    except httpx.HTTPError as exc:
        raise ServiceError(
            "No se pudo subir el archivo a Idonia",
            code="idonia_upload_connection_error",
            details={"reason": str(exc)},
        ) from exc

    if response.status_code >= 400:
        raise ServiceError(
            "Idonia rechazo la subida de archivo",
            code="idonia_upload_http_error",
            details={
                "status_code": response.status_code,
                "response": response.text[:500],
            },
        )

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    inferred_route, file_id = _extract_uploaded_file_reference(payload, file_name)

    return {
        "route": f"/{inferred_route}",
        "file_id": file_id,
        "raw": payload,
    }


async def subir_estudio_idonia(
    *,
    file_name: str,
    file_content: bytes,
    content_type: str = "application/pdf",
    dicom_patient_id: str | None = None,
    dicom_accession_number: str | None = None,
    dicom_study_description: str | None = None,
) -> dict:
    upload_segment = settings.idonia_studies_template.format(num_participante=settings.idonia_num_participante)
    url = f"{settings.idonia_base_url.rstrip('/')}/files/{upload_segment}"

    headers = {
        "Authorization": f"Bearer {_build_idonia_jwt()}",
    }

    files = {
        "file": (file_name, file_content, content_type),
    }
    form_fields = _build_idonia_multipart_fields(
        dicom_patient_id=dicom_patient_id,
        dicom_accession_number=dicom_accession_number,
        dicom_study_description=dicom_study_description,
    )

    try:
        async with httpx.AsyncClient(timeout=settings.integration_timeout_seconds) as client:
            response = await client.post(url, headers=headers, files=files, data=form_fields)
    except httpx.HTTPError as exc:
        raise ServiceError(
            "No se pudo subir el estudio a Idonia",
            code="idonia_study_upload_connection_error",
            details={"reason": str(exc)},
        ) from exc

    if response.status_code >= 400:
        raise ServiceError(
            "Idonia rechazo la subida del estudio",
            code="idonia_study_upload_http_error",
            details={
                "status_code": response.status_code,
                "response": response.text[:500],
            },
        )

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    inferred_route, file_id = _extract_uploaded_file_reference(payload, file_name)

    return {
        "route": f"/{inferred_route}",
        "file_id": file_id,
        "raw": payload,
    }


async def generar_magic_link_info(
    file_reference: str,
    patient_password: str | None = None,
    *,
    include_pin: bool = True,
    expired_creation_mode: str | None = None,
    return_expired: bool = False,
    query_param_override: str | None = None,
) -> str:
    normalized_reference = str(file_reference).lstrip("/")
    query_param = (query_param_override or settings.idonia_magic_link_query_param).strip() or "route"
    magic_link_path = settings.idonia_magic_link_path.lstrip("/")
    query_params: dict[str, str] = {query_param: normalized_reference}
    if expired_creation_mode:
        query_params["expired_creation_mode"] = expired_creation_mode
    if return_expired:
        query_params["return_expired"] = "true"
    query_string = urlencode(query_params, quote_via=quote)
    url = f"{settings.idonia_base_url.rstrip('/')}/{magic_link_path}?{query_string}"

    raw_password = patient_password if patient_password is not None else settings.idonia_patient_password
    body: dict[str, str] = {}
    if raw_password:
        body["password"] = calcular_password_hash_idonia(raw_password)
    if include_pin and settings.idonia_magic_link_pin.strip():
        body["pin"] = settings.idonia_magic_link_pin.strip()
    headers = {
        "Authorization": f"Bearer {_build_idonia_jwt()}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.integration_timeout_seconds) as client:
            response = await client.put(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise ServiceError(
            "No se pudo generar el Magic Link en Idonia",
            code="idonia_magic_link_connection_error",
            details={"reason": str(exc)},
        ) from exc

    if response.status_code >= 400:
        raise ServiceError(
            "Idonia rechazo la generacion del Magic Link",
            code="idonia_magic_link_http_error",
            details={
                "status_code": response.status_code,
                "response": response.text[:500],
            },
        )

    if response.status_code == 204 or not response.text.strip():
        return {
            "url": _build_public_magic_link(normalized_reference),
            "pin": settings.idonia_magic_link_pin.strip() if include_pin else None,
            "raw": {},
        }

    try:
        payload = response.json()
    except ValueError:
        return {
            "url": _build_public_magic_link(normalized_reference),
            "pin": settings.idonia_magic_link_pin.strip() if include_pin else None,
            "raw": {},
        }

    link = _extract_magic_link_url(payload)
    normalized_payload = _build_magic_link_payload(payload)
    pin = None
    if include_pin:
        pin = normalized_payload.get("pin") or normalized_payload.get("PIN") or settings.idonia_magic_link_pin.strip() or None
    if not link:
        link = _build_public_magic_link(normalized_reference)

    return {
        "url": str(link),
        "pin": str(pin) if pin else None,
        "raw": normalized_payload,
    }


async def generar_magic_link(
    file_reference: str,
    patient_password: str | None = None,
    *,
    include_pin: bool = True,
    expired_creation_mode: str | None = None,
    return_expired: bool = False,
    query_param_override: str | None = None,
) -> str:
    result = await generar_magic_link_info(
        file_reference,
        patient_password=patient_password,
        include_pin=include_pin,
        expired_creation_mode=expired_creation_mode,
        return_expired=return_expired,
        query_param_override=query_param_override,
    )
    return str(result["url"])


async def obtener_magic_link(
    file_reference: str,
    patient_password: str | None = None,
    return_expired: bool = False,
) -> dict:
    normalized_reference = str(file_reference).lstrip("/")
    query_param = settings.idonia_magic_link_query_param
    magic_link_path = settings.idonia_magic_link_path.lstrip("/")

    query_params: dict[str, str] = {query_param: normalized_reference}
    if return_expired:
        query_params["return_expired"] = "true"
    query_string = urlencode(query_params, quote_via=quote)
    url = f"{settings.idonia_base_url.rstrip('/')}/{magic_link_path}?{query_string}"

    raw_password = patient_password if patient_password is not None else settings.idonia_patient_password
    if raw_password:
        query_string += "&" + urlencode(
            {"password": calcular_password_hash_idonia(raw_password)},
            quote_via=quote,
        )
        url = f"{settings.idonia_base_url.rstrip('/')}/{magic_link_path}?{query_string}"

    headers = {
        "Authorization": f"Bearer {_build_idonia_jwt()}",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.integration_timeout_seconds) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise ServiceError(
            "No se pudo consultar el Magic Link en Idonia",
            code="idonia_magic_link_lookup_connection_error",
            details={"reason": str(exc)},
        ) from exc

    if response.status_code >= 400:
        raise ServiceError(
            "Idonia rechazo la consulta del Magic Link",
            code="idonia_magic_link_lookup_http_error",
            details={
                "status_code": response.status_code,
                "response": response.text[:500],
            },
        )

    payload: object = {}
    if response.text.strip():
        try:
            payload = response.json()
        except ValueError:
            payload = {}

    normalized_payload = _build_magic_link_payload(payload)
    return {
        "status_code": response.status_code,
        "url": _extract_magic_link_url(payload) or _build_public_magic_link(normalized_reference),
        "pin": normalized_payload.get("pin") or normalized_payload.get("PIN"),
        "is_expired": bool(normalized_payload.get("is_expired", False)),
        "raw": payload,
    }


async def validar_whoami_idonia() -> dict:
    url = f"{settings.idonia_base_url.rstrip('/')}/whoami"
    headers = {
        "Authorization": f"Bearer {_build_idonia_jwt()}",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.integration_timeout_seconds) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise ServiceError(
            "No se pudo consultar whoami en Idonia",
            code="idonia_whoami_connection_error",
            details={"reason": str(exc)},
        ) from exc

    if response.status_code >= 400:
        raise ServiceError(
            "Idonia rechazo la llamada whoami",
            code="idonia_whoami_http_error",
            details={
                "status_code": response.status_code,
                "response": response.text[:500],
            },
        )

    try:
        return response.json()
    except ValueError as exc:
        raise ServiceError(
            "Respuesta no JSON en whoami de Idonia",
            code="idonia_whoami_invalid_json",
            details={"response": response.text[:500]},
        ) from exc


async def descargar_archivo_idonia(route_path: str) -> bytes:
    normalized_route = str(route_path).strip()
    if not normalized_route:
        raise ServiceError(
            "route_path vacio para descargar archivo de Idonia",
            status_code=400,
            code="idonia_empty_route",
        )

    encoded_route = quote(normalized_route, safe="")
    url = f"{settings.idonia_base_url.rstrip('/')}/file?route={encoded_route}"

    headers = {
        "Authorization": f"Bearer {_build_idonia_jwt()}",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.integration_timeout_seconds) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise ServiceError(
            "No se pudo descargar el archivo de Idonia",
            code="idonia_file_download_connection_error",
            details={"reason": str(exc)},
        ) from exc

    if response.status_code >= 400:
        raise ServiceError(
            "Idonia rechazo la descarga del archivo",
            code="idonia_file_download_http_error",
            details={
                "status_code": response.status_code,
                "response": response.text[:500],
            },
        )

    return response.content
