from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status
from jose import jwt
from config import get_settings
from data.users import DEMO_USERS
from models.schemas import ErrorResponse, TokenResponse, UserLogin, UserOut, UserRole

router = APIRouter()
settings = get_settings()


def create_token(user_data: dict) -> str:
    payload = {
        "sub": user_data["id"],
        "role": user_data["role"],
        "name": user_data["full_name"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Credenciales invalidas",
            "content": {
                "application/json": {
                    "example": {
                        "code": "http_401",
                        "message": "Credenciales incorrectas",
                        "details": None,
                        "trace_id": "fca73b5815bc4aa3a318f330dd2fbd44",
                    }
                }
            },
        }
    },
)
def login(body: UserLogin):
    user = DEMO_USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    token = create_token(user)
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user["id"],
            username=body.username,
            full_name=user["full_name"],
            role=user["role"],
        ),
    )


@router.get("/demo-accounts")
def demo_accounts():
    return {
        "doctors": [
            {"username": "dr.garcia", "password": "demo1234", "name": "Dr. Carlos García", "specialty": "Traumatología"},
            {"username": "dr.lopez", "password": "demo1234", "name": "Dra. Ana López", "specialty": "Medicina Interna"},
        ],
        "patients": [
            {"username": "alejandro.m", "password": "demo1234", "name": "Alejandro Martín (rodilla)"},
            {"username": "carmen.r", "password": "demo1234", "name": "Carmen Rodríguez (cardiología)"},
            {"username": "rosa.f", "password": "demo1234", "name": "Rosa Fuentes (neumología)"},
        ],
    }
