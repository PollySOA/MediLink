import json
import re
import unicodedata

from openai import AsyncAzureOpenAI

from config import get_settings
from models.schemas import AvatarMessageResponse, HumanizedReport, ReportComplexity
from prompts.medical_prompts import (
    AVATAR_ELENA_OFFICIAL_REPORT,
    FHIR_EXTRACTION_SYSTEM_PROMPT,
    HUMANIZATION_SYSTEM_PROMPT,
    PRESCRIPTION_HUMANIZATION_PROMPT,
    build_avatar_prompt,
    build_fhir_prompt,
    build_humanization_prompt,
    build_prescription_humanization_prompt,
)

settings = get_settings()

_PLACEHOLDERS = ("your-resource", "your_azure", "your_key", "_here", "placeholder", "change-this")
_REPORT_SCOPE_SENTENCE = "Solo puedo dar informacion orientativa sobre tu informe."
_FEAR_PREFIX = "Entiendo tu preocupacion y quiero explicartelo con calma. "
_RESOLUTION_PREFIX = "Me alegra saber que te ha quedado mas claro. "
_SATISFACTION_REQUEST = "Si te ha ayudado esta explicacion, puedes valorar brevemente la ayuda de Elena de 1 a 5."
_FORBIDDEN_RESPONSE_TOKENS = (
    "ibuprofeno", "paracetamol", "analgesico", "cirugia", "operacion",
    "semanas", "meses", "recuperacion", "infiltracion", "rehabilitacion",
)
_SPANISH_STOP_WORDS = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "u", "en", "con", "sin", "para",
    "por", "del", "al", "que", "como", "se", "su", "sus", "tu", "tus", "mi", "mis", "es", "son", "esta", "este",
    "hay", "me", "te", "lo", "le", "les", "ya", "si", "no", "mas", "muy", "sobre", "solo", "puedo", "dar",
    "informacion", "orientativa", "informe", "hola", "buenas", "vale", "gracias",
}


def _strip_accents(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn")


def _patient_name(patient_context: dict) -> str:
    return patient_context.get("name") or "Paciente"


def _align_patient_name(text: str, patient_name: str) -> str:
    aligned = re.sub(r"\bCarolina\s+Riera\s+Segura\b", patient_name, text, flags=re.IGNORECASE)
    aligned = re.sub(r"\bCarolina\b", patient_name, aligned, flags=re.IGNORECASE)
    return aligned


def _normalize_user_text(text: str) -> str:
    normalized = _strip_accents(text.lower())
    replacements = {
        "rotua": "rotula",
        "rotla": "rotula",
        "rotulla": "rotula",
        "patella": "patela",
        "patele": "patela",
        "patelarrr": "patelar",
        "fisurra": "fisura",
        "fisras": "fisuras",
        "ligamntos": "ligamentos",
        "ligamnetos": "ligamentos",
        "deram": "derrame",
        "derramee": "derrame",
        "liqudo": "liquido",
        "infome": "informe",
        "informee": "informe",
        "rodiya": "rodilla",
        "rodila": "rodilla",
        "montania": "montana",
        "pastiya": "pastilla",
        "grasia": "gracias",
        "grasias": "gracias",
        "entendii": "entendi",
        "aclrado": "aclarado",
        "ecoo": "eco",
        "nodullo": "nodulo",
        "cardiomegaliya": "cardiomegalia",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"\b(eh+|emm+|mmm+|este+|a ver|pues|bueno)\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _is_llm_available() -> bool:
    endpoint = settings.azure_openai_endpoint or ""
    api_key = settings.azure_openai_api_key or ""
    if not endpoint or not api_key:
        return False
    combined = (endpoint + api_key).lower()
    return not any(placeholder in combined for placeholder in _PLACEHOLDERS)


def _client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


def _demo_humanize_report(report_text: str) -> HumanizedReport:
    sentences = [sentence.strip() for sentence in re.split(r"[.;]", report_text) if len(sentence.strip()) > 15]
    summary = (
        "Tu medico ha revisado tu situacion de salud. "
        + (sentences[0].capitalize() + ". " if sentences else "")
        + "El equipo medico te ha preparado este informe para que lo entiendas mejor. "
        "Recuerda seguir las indicaciones de tu medico y preguntar cualquier duda en tu proxima visita."
    )
    findings = [sentence.capitalize() for sentence in sentences[1:4]] or ["Consulta con tu medico los detalles"]
    return HumanizedReport(
        patient_summary=summary,
        complexity=ReportComplexity.medium,
        key_findings=findings,
        recommended_actions="Sigue las indicaciones de tu medico. Si tienes dudas, contacta con tu centro de salud.",
    )


def _demo_extract_fhir_fields(report_text: str) -> dict:
    text_lower = _strip_accents(report_text.lower())
    diagnosis_keywords = ["diagnostico", "diagnosis", "impresion", "conclusion", "hernia", "fractura", "infeccion", "insuficiencia", "estenosis", "neoplasia"]
    conclusion = report_text[:200].strip()
    for keyword in diagnosis_keywords:
        index = text_lower.find(keyword)
        if index != -1:
            conclusion = report_text[index:index + 120].strip()
            break
    return {
        "conclusion": conclusion,
        "category_code": "imaging",
        "category_display": "Imaging",
        "code_code": "55115-0",
        "code_display": "Requested imaging studies information Document",
    }


def _demo_humanize_prescription(prescription_data: dict) -> str:
    medication = prescription_data.get("medication", "el medicamento")
    dosage = prescription_data.get("dosage", "")
    frequency = prescription_data.get("frequency", "")
    duration = prescription_data.get("duration", "")
    instructions = prescription_data.get("instructions", "")
    warnings = prescription_data.get("warnings", [])

    parts = [f"Debes tomar {medication}"]
    if dosage:
        parts.append(f"a dosis de {dosage}")
    if frequency:
        parts.append(frequency)
    if duration:
        parts.append(f"durante {duration}")

    text = " ".join(parts) + "."
    if instructions:
        text += f" {instructions}."
    if warnings:
        text += f" Precauciones: {'; '.join(warnings)}."
    return text


def _tokenize_text(text: str) -> set[str]:
    normalized = _normalize_user_text(text)
    tokens = {
        token for token in re.findall(r"[a-z0-9]+", normalized)
        if len(token) > 2 and token not in _SPANISH_STOP_WORDS
    }
    expanded_tokens = set(tokens)
    if "rotula" in tokens:
        expanded_tokens.add("patela")
    if "patela" in tokens:
        expanded_tokens.add("rotula")
    if "liquido" in tokens:
        expanded_tokens.add("derrame")
    if "derrame" in tokens:
        expanded_tokens.add("liquido")
    return expanded_tokens


def _extract_report_sentences(official_report: str) -> list[str]:
    return [
        sentence.strip(" .;")
        for sentence in re.split(r"(?<=[\.;:])\s+", official_report)
        if len(sentence.strip()) > 15
    ]


def _find_relevant_report_sentences(official_report: str, user_message: str, *, limit: int = 2) -> list[str]:
    user_tokens = _tokenize_text(user_message)
    scored_sentences: list[tuple[int, str]] = []
    for sentence in _extract_report_sentences(official_report):
        sentence_tokens = _tokenize_text(sentence)
        overlap = len(user_tokens & sentence_tokens)
        if overlap > 0:
            scored_sentences.append((overlap, sentence))

    scored_sentences.sort(key=lambda item: (-item[0], len(item[1])))
    if scored_sentences:
        return [sentence for _, sentence in scored_sentences[:limit]]

    if any(token in _normalize_user_text(user_message) for token in ["informe", "resumen", "diagnostico", "hallazgo", "resultado", "conclusion"]):
        return _extract_report_sentences(official_report)[:limit]
    return []


def _analyze_avatar_question(user_message: str, official_report: str) -> dict[str, bool | int]:
    normalized_message = _normalize_user_text(user_message)
    report_tokens = _tokenize_text(official_report)
    user_tokens = _tokenize_text(normalized_message)
    overlap = len(user_tokens & report_tokens)
    return {
        "asks_for_restricted_advice": any(token in normalized_message for token in [
            "pastilla", "ibuprofeno", "paracetamol", "tratamiento", "medic", "cirugia", "operacion",
            "pronostico", "recuperacion", "rehabilitacion", "cuanto tardare", "cuanto tiempo", "que debo tomar",
            "deporte", "trabajar",
        ]),
        "has_fear": any(token in normalized_message for token in ["miedo", "asustada", "asustado", "preocupa", "angustia", "nerviosa", "nervioso"]),
        "asks_about_report": overlap > 0 or any(token in normalized_message for token in ["informe", "resultado", "significa", "explica", "resumen", "hallazgo", "diagnostico", "conclusion"]),
        "confirms_resolved": any(token in normalized_message for token in [
            "gracias", "vale", "de acuerdo", "me quedo claro", "me ha quedado claro", "ya entendi", "entendido",
            "resuelto", "aclarado", "ya esta", "perfecto", "ok gracias",
        ]),
        "off_topic": any(token in normalized_message for token in [
            "embarazo", "covid", "dinero", "familia", "otro problema", "otro tema", "receta general",
            "trabajo", "ansiedad", "depresion",
        ]) and overlap == 0,
        "is_greeting": any(token in normalized_message for token in ["hola", "buenas", "acabo de entrar", "buenos dias", "buenas tardes"]),
        "report_overlap": overlap,
    }


def _build_safe_avatar_voice(user_message: str, patient_context: dict) -> str:
    patient_name = _patient_name(patient_context)
    official_report = patient_context.get("official_report") or AVATAR_ELENA_OFFICIAL_REPORT
    specialty = patient_context.get("specialty") or "tu especialidad"
    analysis = _analyze_avatar_question(user_message, official_report)

    if analysis["confirms_resolved"] and not analysis["off_topic"]:
        voice = f"{patient_name}, {_RESOLUTION_PREFIX}{_SATISFACTION_REQUEST}"
    elif analysis["asks_for_restricted_advice"] or analysis["off_topic"] or (
        not analysis["asks_about_report"] and not analysis["is_greeting"]
    ):
        voice = (
            f"{patient_name}, {_REPORT_SCOPE_SENTENCE} "
            "Si quieres, dime que frase o hallazgo de tu informe te genera duda y te lo explico con claridad."
        )
    elif analysis["is_greeting"]:
        voice = (
            f"{patient_name}, estoy aqui para ayudarte a entender tu informe de {specialty} con calma, claridad y sin inventar informacion. "
            "Puedes preguntarme por cualquier parte del informe y te la explicare en lenguaje sencillo."
        )
    else:
        matched_sentences = _find_relevant_report_sentences(official_report, user_message)
        if matched_sentences:
            matched_text = " ".join(f"{sentence}." for sentence in matched_sentences)
            voice = f"{patient_name}, te lo explico con claridad: segun tu informe, {matched_text}"
        else:
            voice = (
                f"{patient_name}, segun tu informe oficial: {official_report} "
                "Si quieres, puedes preguntarme por una parte concreta y te la aclaro en lenguaje mas sencillo."
            )

    if analysis["has_fear"] and _REPORT_SCOPE_SENTENCE not in voice:
        suffix = voice[len(patient_name) + 2:] if voice.startswith(f"{patient_name}, ") else voice
        suffix = suffix[:1].upper() + suffix[1:] if suffix else suffix
        voice = f"{patient_name}, {_FEAR_PREFIX}{suffix}"

    return voice


def _sanitize_avatar_response(user_message: str, patient_context: dict, candidate_voice: str | None) -> AvatarMessageResponse:
    official_report = patient_context.get("official_report") or AVATAR_ELENA_OFFICIAL_REPORT
    patient_name = _patient_name(patient_context)
    safe_voice = _build_safe_avatar_voice(user_message, patient_context)
    analysis = _analyze_avatar_question(user_message, official_report)
    report_tokens = _tokenize_text(official_report)

    if not candidate_voice:
        final_voice = safe_voice
    else:
        normalized_candidate = " ".join(candidate_voice.split())
        normalized_candidate = _align_patient_name(normalized_candidate, patient_name)
        mentions_forbidden = any(token in normalized_candidate.lower() for token in _FORBIDDEN_RESPONSE_TOKENS)
        candidate_overlap = len(_tokenize_text(normalized_candidate) & report_tokens)

        if analysis["confirms_resolved"] and not analysis["off_topic"]:
            final_voice = f"{patient_name}, {_RESOLUTION_PREFIX}{_SATISFACTION_REQUEST}"
        elif analysis["asks_for_restricted_advice"] or analysis["off_topic"] or (
            analysis["asks_about_report"] and candidate_overlap == 0 and not analysis["is_greeting"]
        ):
            final_voice = safe_voice
        elif mentions_forbidden:
            final_voice = safe_voice
        else:
            final_voice = normalized_candidate
            if analysis["has_fear"] and _FEAR_PREFIX.strip() not in final_voice:
                final_voice = f"{patient_name}, {_FEAR_PREFIX}{final_voice}"
            if analysis["confirms_resolved"] and _SATISFACTION_REQUEST not in final_voice:
                final_voice = final_voice.rstrip(". ") + ". " + _SATISFACTION_REQUEST

    return AvatarMessageResponse(
        justificacion_seguridad="Respuesta limitada al contenido explicito del informe y a reglas clinicas de seguridad, sin inventar tratamiento ni pronostico.",
        respuesta_voz=final_voice,
    )


def _demo_chat_avatar(patient_context: dict, user_message: str) -> AvatarMessageResponse:
    return _sanitize_avatar_response(user_message, patient_context, None)


async def humanize_report(report_text: str, specialty: str | None = None) -> HumanizedReport:
    if not _is_llm_available():
        return _demo_humanize_report(report_text)
    try:
        response = await _client().chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": HUMANIZATION_SYSTEM_PROMPT},
                {"role": "user", "content": build_humanization_prompt(report_text, specialty)},
            ],
            temperature=0.3,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        return HumanizedReport(
            patient_summary=data["patient_summary"],
            complexity=ReportComplexity(data.get("complexity", "medium")),
            key_findings=data.get("key_findings", []),
            recommended_actions=data.get("recommended_actions", ""),
        )
    except Exception:
        return _demo_humanize_report(report_text)


async def extract_fhir_fields(report_text: str) -> dict:
    if not _is_llm_available():
        return _demo_extract_fhir_fields(report_text)
    try:
        response = await _client().chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": FHIR_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": build_fhir_prompt(report_text)},
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return _demo_extract_fhir_fields(report_text)


async def humanize_prescription(prescription_data: dict) -> str:
    if not _is_llm_available():
        return _demo_humanize_prescription(prescription_data)
    try:
        response = await _client().chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": PRESCRIPTION_HUMANIZATION_PROMPT},
                {"role": "user", "content": build_prescription_humanization_prompt(prescription_data)},
            ],
            temperature=0.4,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return _demo_humanize_prescription(prescription_data)


async def chat_with_avatar(
    patient_context: dict,
    conversation_history: list[dict],
    user_message: str,
) -> AvatarMessageResponse:
    if not _is_llm_available():
        return _demo_chat_avatar(patient_context, user_message)
    try:
        messages = build_avatar_prompt(patient_context, conversation_history, user_message)
        response = await _client().chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=messages,
            temperature=0.6,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        return _sanitize_avatar_response(
            user_message,
            patient_context,
            data.get("respuesta_voz"),
        )
    except Exception:
        return _demo_chat_avatar(patient_context, user_message)
