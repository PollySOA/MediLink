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

_RECOMMENDED_ACTIONS_PREFIX = (
    "Si quieres, puedo ayudarte a entender una parte concreta del resultado con palabras mas sencillas. "
    "Si te quedan dudas clinicas importantes, comentalas con tu medico para recibir la explicacion adaptada a tu caso."
)

_MEDICAL_GLOSSARY = {
    "lesion": "lesion (zona danada o afectada)",
    "lesiones": "lesiones (zonas danadas o afectadas)",
    "hallazgo": "hallazgo (algo que se ha visto en el informe)",
    "hallazgos": "hallazgos (cosas que se han visto en el informe)",
    "alteracion": "alteracion (cambio respecto a lo esperado)",
    "alteraciones": "alteraciones (cambios respecto a lo esperado)",
    "inflamacion": "inflamacion (hinchazon o irritacion)",
    "edema": "edema (hinchazon por acumulacion de liquido)",
    "dolor": "dolor (molestia)",
    "cronico": "cronico (que dura mucho tiempo)",
    "agudo": "agudo (que aparece de forma reciente o intensa)",
    "leve": "leve (poco intenso)",
    "moderado": "moderado (de intensidad intermedia)",
    "severo": "severo (de intensidad alta)",
    "bilateral": "bilateral (en ambos lados)",
    "unilateral": "unilateral (en un solo lado)",
    "compatible": "compatible (encaja con)",
    "sugestivo": "sugestivo (hace pensar en)",
    "patologia": "patologia (problema de salud)",
    "patologico": "patologico (que no es normal)",
    "degenerativo": "degenerativo (desgaste progresivo)",
    "artrosis": "artrosis (desgaste de la articulacion)",
    "hernia": "hernia (salida de una parte de tejido o material)",
    "fractura": "fractura (rotura del hueso)",
    "fisura": "fisura (pequena grieta)",
    "quiste": "quiste (bolsa o cavidad con contenido)",
    "nodule": "nodulo (pequena masa o bulto)",
    "nodulo": "nodulo (pequena masa o bulto)",
    "tumor": "tumor (masa o crecimiento anormal)",
    "benigno": "benigno (no canceroso)",
    "maligno": "maligno (con capacidad de crecer de forma perjudicial)",
    "infeccion": "infeccion (cuando hay germenes causando problemas)",
    "vascular": "vascular (relacionado con los vasos sanguineos)",
    "neurologico": "neurologico (relacionado con nervios o cerebro)",
    "muscular": "muscular (relacionado con los musculos)",
    "ligamento": "ligamento (banda que da estabilidad a la articulacion)",
    "ligamentos": "ligamentos (bandas que dan estabilidad a la articulacion)",
    "cartilago": "cartilago (tejido flexible que amortigua la articulacion)",
    "tendon": "tendon (estructura que une musculo y hueso)",
    "tendones": "tendones (estructuras que unen musculo y hueso)",
    "menisco": "menisco (pieza que amortigua la rodilla)",
    "meniscos": "meniscos (piezas que amortiguan la rodilla)",
    "sinovial": "sinovial (relacionado con el liquido de la articulacion)",
    "articulacion": "articulacion (zona donde se unen dos huesos)",
    "articulaciones": "articulaciones (zonas donde se unen dos huesos)",
}


def _strip_accents(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn")


def _patient_name(patient_context: dict) -> str:
    return patient_context.get("name") or "Paciente"


def _align_patient_name(text: str, patient_name: str) -> str:
    aligned = re.sub(r"\bCarolina\s+Riera\s+Segura\b", patient_name, text, flags=re.IGNORECASE)
    aligned = re.sub(r"\bCarolina\b", patient_name, aligned, flags=re.IGNORECASE)
    return aligned


def _medical_term_hint(term: str) -> str | None:
    normalized = _strip_accents(term.lower())
    if normalized in _MEDICAL_GLOSSARY:
        return _MEDICAL_GLOSSARY[normalized]

    suffix_hints = [
        ("itis", "inflamacion o irritacion"),
        ("algia", "dolor"),
        ("osis", "cambio o proceso"),
        ("patia", "problema o alteracion"),
        ("megalia", "aumento de tamano"),
        ("emia", "relacionado con la sangre"),
        ("uria", "relacionado con la orina"),
        ("scopia", "revision o vision interna"),
        ("grama", "registro o imagen"),
        ("plastia", "reparacion o reconstruccion"),
        ("ectomia", "extirpacion"),
        ("cele", "abultamiento o hernia"),
        ("oma", "masa o bulto"),
        ("osis", "desgaste o cambio"),
    ]
    for suffix, hint in suffix_hints:
        if normalized.endswith(suffix) and len(normalized) >= len(suffix) + 3:
            return hint
    return None


def _annotate_medical_terms(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        hint = _medical_term_hint(word)
        if not hint:
            return word
        normalized_word = _strip_accents(word.lower())
        if hint.lower() in normalized_word:
            return word
        if normalized_word in {
            "articulacion", "articulaciones", "ligamento", "ligamentos", "cartilago", "tendon", "tendones",
            "menisco", "meniscos", "fractura", "fisura", "quiste", "nodulo", "tumor", "infeccion", "lesion", "lesiones",
            "sinovial", "vascular", "neurologico", "muscular",
        }:
            return word
        return f"{word} ({hint})"

    annotated = re.sub(r"\b[\w-]{5,}\b(?!\s*\()", replace, text)
    annotated = re.sub(r"\s+", " ", annotated).strip()
    return annotated


def _simplify_clinical_language(text: str) -> str:
    simplified = _strip_accents(text)
    replacements = [
        (r"\brm de rodilla\b", "resonancia de rodilla"),
        (r"\barticulacion femoropatelar\b", "la zona de la rodilla que une el femur con la rotula"),
        (r"\bfemoropatelares\b", "relacionados con la zona entre el femur y la rotula"),
        (r"\bfemoropatelar\b", "de la zona entre el femur y la rotula"),
        (r"\bpatela alta\b", "la rotula esta mas alta de lo normal"),
        (r"\bfaceta patelar externa\b", "la parte externa de la rotula"),
        (r"\bderrame articular\b", "acumulacion de liquido en la articulacion"),
        (r"\bsin derrame articular\b", "sin acumulacion de liquido en la articulacion"),
        (r"\bmeniscos conservados y sanos\b", "los meniscos estan bien"),
        (r"\bligamentos estan conservados y sanos\b", "los ligamentos estan bien"),
        (r"\bfisuras de grado ii-iii\b", "pequenas fisuras de grado II-III"),
        (r"\bfisuras grado ii-iii\b", "pequenas fisuras de grado II-III"),
        (r"\bsobrecarga patelar\b", "sobrecarga en la rotula"),
        (r"\bconclusion:\b", "en resumen:"),
        (r"\bsin lesion meniscal ni ligamentosa\b", "sin lesion en meniscos ni ligamentos"),
        (r"\bsin lesion de meniscos ni ligamentosa\b", "sin lesion en meniscos ni ligamentos"),
        (r"\bsin lesion de meniscos ni ligamentaria\b", "sin lesion en meniscos ni ligamentos"),
        (r"\bpatelar externa\b", "externa de la rotula"),
    ]
    for pattern, replacement in replacements:
        simplified = re.sub(pattern, replacement, simplified, flags=re.IGNORECASE)
    simplified = re.sub(r"\bcon la rotula(?:\s+con la rotula)+\b", "con la rotula", simplified, flags=re.IGNORECASE)
    simplified = re.sub(r"\bla rotula esta mas alta de lo normal\b\s+con la rotula\b", "la rotula esta mas alta de lo normal", simplified, flags=re.IGNORECASE)
    simplified = _annotate_medical_terms(simplified)
    simplified = simplified.replace(" .", ".")
    return simplified


def _patient_friendly_voice(user_message: str, patient_context: dict, *, source_text: str) -> str:
    patient_name = _patient_name(patient_context)
    official_report = patient_context.get("official_report") or AVATAR_ELENA_OFFICIAL_REPORT
    analysis = _analyze_avatar_question(user_message, official_report)

    simple_text = _simplify_clinical_language(source_text)
    base = f"En palabras sencillas, tu informe dice: {simple_text}."
    if analysis["has_fear"]:
        base = f"Entiendo que esto pueda preocuparte. Vamos paso a paso. {base}"
    return f"{patient_name}, {base} Si quieres, te explico una parte concreta con todavía más calma."


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
    clauses = [sentence.strip() for sentence in re.split(r"[.;\n]+", report_text) if len(sentence.strip()) > 12]
    salient_clauses = clauses[:4]
    if salient_clauses:
        first_clause = salient_clauses[0].rstrip(".")
        summary = (
            "El informe resume estos hallazgos en lenguaje tecnico: "
            f"{first_clause[0].lower() + first_clause[1:] if first_clause else first_clause}. "
            "Dicho de forma sencilla, el resultado describe lo que se ha encontrado y ayuda a que tu medico lo valore contigo con mas contexto. "
            "La idea es que puedas entenderlo con calma, sin sacar conclusiones por tu cuenta."
        )
    else:
        summary = (
            "El informe describe un resultado clinico que conviene leer con calma y en contexto. "
            "Este resumen intenta explicarlo de forma sencilla sin añadir nada que no aparezca en el texto original."
        )

    findings = [
        clause[0].upper() + clause[1:] if clause else clause
        for clause in salient_clauses[1:4]
    ] or ["Revisa el informe completo con tu medico para interpretarlo en contexto."]
    complexity = ReportComplexity.low
    if len(clauses) >= 4:
        complexity = ReportComplexity.high
    elif len(clauses) >= 2:
        complexity = ReportComplexity.medium

    if any(keyword in _strip_accents(report_text.lower()) for keyword in ["urgente", "grave", "critico", "complicacion", "fractura", "hemorragia", "tumor"]):
        complexity = ReportComplexity.high

    return HumanizedReport(
        patient_summary=summary,
        complexity=complexity,
        key_findings=findings,
        recommended_actions=_RECOMMENDED_ACTIONS_PREFIX,
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
    elif analysis["asks_for_restricted_advice"] or analysis["off_topic"]:
        voice = (
            f"{patient_name}, {_REPORT_SCOPE_SENTENCE} "
            "Si quieres, dime que parte exacta del informe te genera duda y te la explico en palabras sencillas."
        )
    elif analysis["has_fear"]:
        matched_sentences = _find_relevant_report_sentences(official_report, user_message)
        source_text = " ".join(matched_sentences) if matched_sentences else official_report
        voice = _patient_friendly_voice(user_message, patient_context, source_text=source_text)
    elif analysis["is_greeting"]:
        voice = (
            f"Hola {patient_name}, estoy aqui para ayudarte a entender tu informe de {specialty} con calma y sin tecnicismos. "
            "Si algo te preocupa, dime qué parte quieres revisar y te la explico paso a paso."
        )
    else:
        matched_sentences = _find_relevant_report_sentences(official_report, user_message)
        if matched_sentences:
            matched_text = " ".join(matched_sentences)
            voice = _patient_friendly_voice(user_message, patient_context, source_text=matched_text)
        else:
            voice = _patient_friendly_voice(user_message, patient_context, source_text=official_report)

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
        normalized_candidate = _simplify_clinical_language(normalized_candidate)
        mentions_forbidden = any(token in normalized_candidate.lower() for token in _FORBIDDEN_RESPONSE_TOKENS)
        candidate_overlap = len(_tokenize_text(normalized_candidate) & report_tokens)

        if analysis["confirms_resolved"] and not analysis["off_topic"]:
            final_voice = f"{patient_name}, {_RESOLUTION_PREFIX}{_SATISFACTION_REQUEST}"
        elif analysis["asks_for_restricted_advice"] or analysis["off_topic"]:
            final_voice = safe_voice
        elif analysis["has_fear"]:
            final_voice = safe_voice
        elif mentions_forbidden:
            final_voice = safe_voice
        else:
            final_voice = normalized_candidate
            if analysis["has_fear"] and "Entiendo que esto pueda preocuparte" not in final_voice:
                final_voice = f"{patient_name}, Entiendo que esto pueda preocuparte. Vamos paso a paso. {final_voice}"
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
            temperature=0.2,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        summary = " ".join(str(data.get("patient_summary", "")).split())
        findings = [" ".join(str(item).split()) for item in data.get("key_findings", []) if str(item).strip()]
        recommended_actions = " ".join(str(data.get("recommended_actions", "")).split())
        return HumanizedReport(
            patient_summary=summary or _demo_humanize_report(report_text).patient_summary,
            complexity=ReportComplexity(data.get("complexity", "medium")),
            key_findings=findings or _demo_humanize_report(report_text).key_findings,
            recommended_actions=recommended_actions or _demo_humanize_report(report_text).recommended_actions,
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
