from models.schemas import UserRole

DEMO_USERS = {
    "dr.garcia": {
        "id": "DOC-001",
        "username": "dr.garcia",
        "password": "demo1234",
        "full_name": "Dr. Carlos García Fernández",
        "role": UserRole.doctor,
        "specialty": "Traumatología y Cirugía Ortopédica",
        "license_number": "28-056789",
    },
    "dr.lopez": {
        "id": "DOC-002",
        "username": "dr.lopez",
        "password": "demo1234",
        "full_name": "Dra. Ana López Martínez",
        "role": UserRole.doctor,
        "specialty": "Medicina Interna",
        "license_number": "33-012345",
    },
    "carmen.r": {
        "id": "PAT-001",
        "username": "carmen.r",
        "password": "demo1234",
        "full_name": "Carmen Rodríguez Vega",
        "role": UserRole.patient,
    },
    "alejandro.m": {
        "id": "PAT-002",
        "username": "alejandro.m",
        "password": "demo1234",
        "full_name": "Carolina Riera Segura",
        "role": UserRole.patient,
    },
    "carolina.r": {
        "id": "PAT-002",
        "username": "carolina.r",
        "password": "demo1234",
        "full_name": "Carolina Riera Segura",
        "role": UserRole.patient,
    },
    "rosa.f": {
        "id": "PAT-003",
        "username": "rosa.f",
        "password": "demo1234",
        "full_name": "Rosa Elena Fuentes",
        "role": UserRole.patient,
    },
    "miguel.d": {
        "id": "PAT-004",
        "username": "miguel.d",
        "password": "demo1234",
        "full_name": "Miguel Ángel Domínguez",
        "role": UserRole.patient,
    },
    "isabel.m": {
        "id": "PAT-005",
        "username": "isabel.m",
        "password": "demo1234",
        "full_name": "Isabel Méndez Ruiz",
        "role": UserRole.patient,
    },
}

USER_BY_ID = {v["id"]: v for v in DEMO_USERS.values()}
