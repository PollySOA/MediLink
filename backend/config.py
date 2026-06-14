from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    idonia_public_id: str = ""
    idonia_api_secret: str = ""
    idonia_api_key: str = ""
    # Compatibilidad temporal con configuraciones previas.
    idonia_api_url: str = ""
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
    idonia_source_report_pdf_path: str = ""
    idonia_source_study_file_path: str = ""

    recog_api_url: str = "https://api.recog.es/relisten/dictation/process/report-results"
    recog_api_key: str = ""
    recog_auth_mode: str = "auto"
    recog_auth_base_url: str = "https://api.recog.es/auth"
    recog_client_id: str = ""
    recog_client_secret: str = ""
    recog_strict_mode: bool = False

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "Phi-3.5-mini-instruct"
    azure_openai_api_version: str = "2024-02-01"

    integration_timeout_seconds: float = 60.0

    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    app_env: str = "development"
    
    # CORS: comma-separated list of allowed origins
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    # Evita inconsistencias cuando el backend usa connect-staging y el visor apunta a produccion.
    if (
        "connect-staging.idonia.com" in settings.idonia_base_url
        and settings.idonia_magic_link_public_base_url.startswith("https://idonia.com/v/")
    ):
        settings.idonia_magic_link_public_base_url = settings.idonia_magic_link_public_base_url.replace(
            "https://idonia.com/v/",
            "https://staging.idonia.com/v/",
            1,
        )

    return settings
