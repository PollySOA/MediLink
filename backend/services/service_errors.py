class ServiceError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        code: str = "integration_error",
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}

    def as_http_detail(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }
