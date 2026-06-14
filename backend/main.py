import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import reports, patients, fhir, demo, auth, doctor, avatar, idonia_v1
from config import get_settings

app = FastAPI(
    title="MediLink — Interoperabilidad y Humanización Médica",
    description="I Hackathon IABiomed · Reto Idonia. Sistema con roles médico/paciente, avatar IA orientativo, FHIR R4 e integración con la plataforma Idonia.",
    version="2.0.0",
)

settings = get_settings()

# Parse allowed origins from comma-separated string
allowed_origins_list = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(doctor.router,   prefix="/api/doctor",   tags=["Doctor"])
app.include_router(reports.router,  prefix="/api/reports",  tags=["Reports"])
app.include_router(fhir.router,     prefix="/api/fhir",     tags=["FHIR"])
app.include_router(avatar.router,   prefix="/api/avatar",   tags=["Avatar"])
app.include_router(demo.router,     prefix="/api/demo",     tags=["Demo"])
app.include_router(idonia_v1.router, prefix="/api/v1", tags=["Idonia V1"])


@app.middleware("http")
async def attach_trace_id(request: Request, call_next):
    request.state.trace_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    response = await call_next(request)
    response.headers["x-trace-id"] = request.state.trace_id
    return response


def _build_error_payload(*, code: str, message: str, details: object, trace_id: str) -> dict:
    return {
        "code": code,
        "message": message,
        "details": details,
        "trace_id": trace_id,
    }


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    trace_id = getattr(request.state, "trace_id", uuid.uuid4().hex)
    detail = exc.detail

    message = detail if isinstance(detail, str) else "Solicitud rechazada"
    details = None if isinstance(detail, str) else detail

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_payload(
            code=f"http_{exc.status_code}",
            message=message,
            details=details,
            trace_id=trace_id,
        ),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(request: Request, exc: RequestValidationError):
    trace_id = getattr(request.state, "trace_id", uuid.uuid4().hex)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_build_error_payload(
            code="validation_error",
            message="Error de validacion en la solicitud",
            details=exc.errors(),
            trace_id=trace_id,
        ),
    )


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, _: Exception):
    trace_id = getattr(request.state, "trace_id", uuid.uuid4().hex)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_payload(
            code="internal_error",
            message="Error interno no controlado",
            details=None,
            trace_id=trace_id,
        ),
    )


@app.get("/")
def root():
    return {"project": "MediLink", "hackathon": "IABiomed 2025", "docs": "/docs"}
