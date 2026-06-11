from models.schemas import AvatarMessageResponse
from services.azure_llm_service import chat_with_avatar
from services.service_errors import ServiceError


async def chat_avatar_elena(
    *,
    patient_context: dict,
    conversation_history: list[dict],
    user_message: str,
) -> AvatarMessageResponse:
    try:
        return await chat_with_avatar(
            patient_context=patient_context,
            conversation_history=conversation_history,
            user_message=user_message,
        )
    except Exception as exc:
        raise ServiceError(
            "Fallo el pipeline del Avatar Elena",
            code="avatar_pipeline_error",
            details={"reason": str(exc)},
        ) from exc
