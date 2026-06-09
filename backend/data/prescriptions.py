from models.schemas import Prescription
from datetime import datetime, timezone

PRESCRIPTIONS: dict[str, list[Prescription]] = {
    "PAT-002": [
        Prescription(
            id="RX-001",
            patient_id="PAT-002",
            doctor_id="DOC-001",
            doctor_name="Dr. Carlos García Fernández",
            medication="Ibuprofeno",
            dosage="600mg",
            frequency="Cada 8 horas",
            duration="5 días",
            instructions="Tomar con alimentos para evitar molestias gástricas. Aplicar hielo en la rodilla 20 minutos, 3 veces al día. Reposo relativo, evitar deportes de impacto.",
            warnings=["No tomar con el estómago vacío", "No conducir si sientes mareo", "Consulta si el dolor aumenta"],
            created_at=datetime(2025, 6, 5, 10, 30, tzinfo=timezone.utc),
            humanized_instructions="Tu médico te ha recetado ibuprofeno para calmar el dolor e inflamación de la rodilla. Tómalo 3 veces al día con la comida. También es importante que apliques frío en la rodilla y evites correr o saltar hasta la próxima revisión.",
        )
    ],
    "PAT-001": [],
    "PAT-003": [],
    "PAT-004": [],
    "PAT-005": [],
}
