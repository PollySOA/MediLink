import re
from functools import lru_cache

from pydantic_settings import BaseSettings


_RECOG_API_KEY_PATTERN = re.compile(r"^rrk_[A-Za-z0-9-]+_[A-Za-z0-9._-]+$")


class Settings(BaseSettings):
    idonia_public_id: str = ""
    idonia_api_secret: str = ""
    idonia_api_key: str = ""
    idonia_base_url: str = "https://connect-staging.idonia.com"
    idonia_upload_template: str = "report_hak_{num_participante}"
    idonia_studies_template: str = "dicom_hak_{num_participante}"
    idonia_magic_link_path: str = "/ml"
    idonia_magic_link_query_param: str = "route"
    idonia_magic_link_public_base_url: str = ""
    idonia_magic_link_reference_mode: str = "file_id"
    idonia_magic_link_pin: str = ""
    idonia_num_participante: str = "000"
    idonia_patient_password: str = ""
    idonia_source_study_file_path: str = ""

    recog_api_url: str = "https://api.recog.es/relisten/dictation/process/report-results"
    recog_api_key: str = ""
    recog_auth_mode: str = "api_key"
    recog_auth_base_url: str = "https://api.recog.es/auth"
    recog_client_id: str = ""
    recog_client_secret: str = ""
    recog_strict_mode: bool = True

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "Phi-3.5-mini-instruct"
    azure_openai_api_version: str = "2024-02-01"

    integration_timeout_seconds: float = 60.0

    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    app_env: str = "development"
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    cors_allow_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://app-medilink-web-fr-.*\.azurewebsites\.net"

    class Config:
        env_file = ".env"
        extra = "ignore"


def _validate_clinical_essentials(settings: Settings) -> None:
    if not settings.recog_strict_mode:
        return

    idonia_api_secret = (settings.idonia_api_secret or "").strip()
    recog_api_key = (settings.recog_api_key or "").strip()

    if not idonia_api_secret.startswith("S2"):
        raise SystemExit(
            "Configuracion invalida: IDONIA_API_SECRET debe comenzar por 'S2' cuando RECOG_STRICT_MODE=true"
        )

    if not _RECOG_API_KEY_PATTERN.fullmatch(recog_api_key):
        raise SystemExit(
            "Configuracion invalida: RECOG_API_KEY debe tener formato 'rrk_<publicId>_<secret>' cuando RECOG_STRICT_MODE=true"
        )

    if not settings.idonia_base_url.lower().startswith("https://"):
        raise SystemExit("Configuracion invalida: IDONIA_BASE_URL debe usar HTTPS")

    if not settings.recog_api_url.lower().startswith("https://"):
        raise SystemExit("Configuracion invalida: RECOG_API_URL debe usar HTTPS")

    azure_endpoint = (settings.azure_openai_endpoint or "").strip()
    if azure_endpoint and not azure_endpoint.lower().startswith("https://"):
        raise SystemExit("Configuracion invalida: AZURE_OPENAI_ENDPOINT debe usar HTTPS")

    app_env = (settings.app_env or "development").strip().lower()
    jwt_secret = (settings.jwt_secret or "").strip().lower()
    if app_env not in {"development", "dev", "local"} and (
        not jwt_secret or "change-this" in jwt_secret
    ):
        raise SystemExit(
            "Configuracion invalida: JWT_SECRET debe ser fuerte y no usar placeholder fuera de desarrollo"
        )


def _normalize_staging_magic_link(settings: Settings) -> None:
    if (
        "connect-staging.idonia.com" in settings.idonia_base_url
        and settings.idonia_magic_link_public_base_url.startswith("https://idonia.com/v/")
    ):
        settings.idonia_magic_link_public_base_url = settings.idonia_magic_link_public_base_url.replace(
            "https://idonia.com/v/",
            "https://staging.idonia.com/v/",
            1,
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _normalize_staging_magic_link(settings)
    _validate_clinical_essentials(settings)
    return settings
