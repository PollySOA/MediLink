import base64
import hashlib
import hmac
import json
import time

from services.service_errors import ServiceError


def decode_idonia_secret(api_secret: str) -> bytes:
    raw = (api_secret or "").strip()
    if not raw.startswith("S2"):
        raise ServiceError(
            "API secret de Idonia invalido: debe comenzar por prefijo S2",
            status_code=500,
            code="idonia_invalid_api_secret_prefix",
        )

    encoded = raw[2:]
    padding = "=" * (-len(encoded) % 4)
    try:
        return base64.urlsafe_b64decode(encoded + padding)
    except Exception as exc:
        raise ServiceError(
            "API secret de Idonia no valido para decodificacion URL-safe Base64",
            status_code=500,
            code="idonia_invalid_api_secret_format",
            details={"reason": str(exc)},
        ) from exc


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def generate_jwt_hs256(public_id: str, api_secret: str) -> str:
    secret_bytes = decode_idonia_secret(api_secret)
    now = int(time.time())
    iat = now - 300
    exp = now + 300

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": public_id,
        "iat": iat,
        "exp": exp,
    }

    encoded_header = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret_bytes, signing_input, hashlib.sha256).digest()

    return f"{encoded_header}.{encoded_payload}.{b64url_encode(signature)}"
