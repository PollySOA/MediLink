import uuid
from datetime import datetime, timezone
from models.schemas import FHIRDiagnosticReport


def build_diagnostic_report(report_text: str, patient_id: str, fhir_fields: dict) -> FHIRDiagnosticReport:
    now = datetime.now(timezone.utc).isoformat()
    specialty = fhir_fields.get("specialty_display", "Diagnóstico por imagen")
    return FHIRDiagnosticReport(
        id=str(uuid.uuid4()),
        status=fhir_fields.get("status", "final"),
        category=[{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD", "display": specialty}]}],
        code={"coding": [{"system": "http://loinc.org", "code": "18748-4", "display": "Diagnostic imaging study"}], "text": specialty},
        subject={"reference": f"Patient/{patient_id}", "display": "Paciente ficticio (demo)"},
        effective_datetime=now,
        issued=now,
        conclusion=fhir_fields.get("conclusion", report_text[:200]),
    )
