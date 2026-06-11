from fastapi import APIRouter

router = APIRouter()


@router.get("/metadata")
def fhir_capability_statement():
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{"mode": "server", "resource": [{"type": "DiagnosticReport"}]}],
    }
