from typing import TypedDict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import get_settings
from data.users import USER_BY_ID
from data.fictional_patients import FictionalPatient
from models.schemas import UserRole


class AuthenticatedUser(TypedDict):
    id: str
    role: UserRole
    full_name: str


settings = get_settings()
_security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = str(payload.get("sub") or "")
        role_value = str(payload.get("role") or "")
        full_name = str(payload.get("name") or "Usuario")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido") from exc

    if not user_id or not role_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")

    try:
        role = UserRole(role_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Rol de token invalido") from exc

    known_user = USER_BY_ID.get(user_id)
    if known_user:
        full_name = str(known_user.get("full_name") or full_name)

    return AuthenticatedUser(id=user_id, role=role, full_name=full_name)


def get_current_doctor(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if current_user["role"] != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo acceso para medicos")
    return current_user


def can_view_patient(current_user: AuthenticatedUser, patient: FictionalPatient) -> bool:
    if current_user["role"] == UserRole.doctor:
        return True
    if current_user["role"] == UserRole.patient:
        return patient.id == current_user["id"]
    return False


def can_edit_patient(current_user: AuthenticatedUser, patient: FictionalPatient) -> bool:
    if current_user["role"] == UserRole.doctor:
        return patient.assigned_doctor_id == current_user["id"]
    if current_user["role"] == UserRole.patient:
        return patient.id == current_user["id"]
    return False


def can_prescribe_patient(current_user: AuthenticatedUser, patient: FictionalPatient) -> bool:
    return current_user["role"] == UserRole.doctor and patient.assigned_doctor_id == current_user["id"]
