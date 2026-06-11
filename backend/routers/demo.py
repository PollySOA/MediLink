from fastapi import APIRouter
from data.fictional_patients import FICTIONAL_PATIENTS

router = APIRouter()


@router.get("/flow")
def demo_flow():
    return {
        "project": "MediLink — Interoperabilidad y Humanización Médica",
        "hackathon": "I Hackathon IABiomed · Reto Idonia",
        "roles": ["doctor", "patient"],
        "flow": [
            {"step": 1, "actor": "médico", "action": "Sube o dicta informe médico"},
            {"step": 2, "actor": "sistema", "action": "LLM humaniza el informe (Phi-3.5-mini)"},
            {"step": 3, "actor": "sistema", "action": "Genera recurso FHIR R4 DiagnosticReport"},
            {"step": 4, "actor": "sistema", "action": "Genera PDF accesible vía API Idonia"},
            {"step": 5, "actor": "paciente", "action": "Recibe resumen en lenguaje claro"},
            {"step": 6, "actor": "paciente", "action": "Habla con Elena (avatar orientativo IA)"},
            {"step": 7, "actor": "médico", "action": "Emite receta con instrucciones humanizadas"},
        ],
        "demo_accounts": {
            "doctor": "dr.garcia / demo1234",
            "patient": "alejandro.m / demo1234",
        }
    }


@router.get("/idonia-link")
def idonia_demo_link():
    return {
        "available": False,
        "description": "Acceso de demo no expuesto por API. Configuralo localmente en variables de entorno.",
    }
