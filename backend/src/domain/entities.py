from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClinicalIdentity:
    patient_id: str
    dicom_patient_id: str
    dicom_accession_number: str
    dicom_study_description: str
    route: str


@dataclass(frozen=True)
class ClinicalOrchestrationResult:
    route: str
    report_upload: dict[str, Any]
    study_upload: dict[str, Any]
    humanized_upload: dict[str, Any]
    magic_link_url: str
    magic_link_pin: str | None
