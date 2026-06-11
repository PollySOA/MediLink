# MediLink — Interoperabilidad y Humanización Médica
**I Hackathon IABiomed · Reto Idonia · Entrega 15 junio**

Desarrollado por desarrolladora fullstack con formación en Ingeniería de IA Generativa.

---

## Qué hace este sistema

```
MÉDICO                          PACIENTE
  |                                |
  | Sube/dicta informe             | Inicia sesión
  |         |                      |
  v         v                      v
[FastAPI Backend]           [React Frontend]
     |                            |
     |-- Phi-3.5-mini (Azure) --> Humanización del informe
     |-- FHIR R4 Builder -------> DiagnosticReport exportable
     |-- API Idonia (recog.es) -> PDF con Magic Link + QR
     |-- Avatar Elena (LLM) ----> Chat enfermera IA con el paciente
     |-- Recetas humanizadas ----> El paciente entiende su medicación
```

## Roles del sistema

| Rol | Funciones |
|-----|-----------|
| Médico | Ver pacientes, procesar informes (FHIR + humanización), emitir recetas explicadas |
| Paciente | Ver informe explicado, ver recetas en lenguaje claro, chatear con Elena (enfermera IA) |

## Cuentas de demo

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `dr.garcia` | demo1234 | Médico — Traumatología |
| `dr.lopez` | demo1234 | Médico — Medicina Interna |
| `alejandro.m` | demo1234 | Paciente — Lesión de rodilla |
| `carmen.r` | demo1234 | Paciente — Cardiología |
| `rosa.f` | demo1234 | Paciente — Neumología |

---

## Instalación en VS Code

```bash
# Abrir workspace
code medilink.code-workspace
```

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # editar con tus claves
uvicorn main:app --reload --port 8000
```

Swagger en: http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev
```

App en: http://localhost:5173

---

## Azure for Students — Phi-3.5-mini (gratis)

1. Ir a https://ai.azure.com
2. Crear un proyecto
3. Model catalog → buscar `Phi-3.5-mini-instruct`
4. Deploy as Serverless API
5. Copiar endpoint y key al `.env`

---

## Demo Idonia real

- La demo Idonia se configura desde el backend mediante variables locales de entorno.
- No publiques credenciales ni enlaces de acceso en este README.

---

## Ingeniería de prompts aplicada

Todos los prompts siguen la estructura Role / Goal / Context / Constraints / Output Format del curso de Ingeniería de IA Generativa:

- Humanización de informes: temperatura 0.3, JSON forzado, few-shot, guardrail anti-alucinaciones
- FHIR extraction: temperatura 0.1 para máxima precisión
- Avatar Elena: temperatura 0.6 para naturalidad conversacional, contexto del paciente inyectado
- Recetas: humanización empática manteniendo dosis exactas del médico

---

## Consideraciones éticas (AI Act — alto riesgo)

- Datos de demo 100% ficticios
- El sistema no diagnostica ni modifica tratamientos
- Disclaimer obligatorio en todos los informes generados
- Guardrails explícitos en prompts contra invención de información médica

---

## Checklist de cierre (Idonia)

Estado actual validado en local:

- `GET /api/reports/idonia/whoami` responde 200 y devuelve identidad ICC.
- `POST /api/reports/patients/{id}/idonia-link` funciona para `report` y `study`.
- `expired_creation_mode` soportado en `create | skip | update`.
- `GET /api/reports/idonia/open/{access_id}` redirige con `307` a `https://staging.idonia.com/v/hacknum23?url=...`.
- `GET /api/reports/idonia/magic-link` soporta `return_expired=true`.
- Modo estricto de referencia configurable por entorno:
  - `IDONIA_MAGIC_LINK_REFERENCE_MODE=file_id` (compatibilidad)
  - `IDONIA_MAGIC_LINK_REFERENCE_MODE=route_folder` (alineado con manual)
  - `IDONIA_MAGIC_LINK_REFERENCE_MODE=route_full` (ruta completa)

### Variables nuevas de configuración

- `IDONIA_MAGIC_LINK_REFERENCE_MODE`: selecciona cómo construir la referencia para `/ml`.

### Troubleshooting rápido

- `405 Method Not Allowed`:
  - `idonia-link` es `POST` (no `GET`).
  - `idonia/open/{id}` es `GET`; no usar `HEAD` (`curl -I`).
- `404 Acceso expirado o no encontrado` en `open/{id}`:
  - El `access_id` es de un solo uso y se invalida al abrir.
- `status_code: 204` en `GET /idonia/magic-link`:
  - No existe Magic Link para la ruta consultada (comportamiento esperado de ICC).

### Pendiente externo al código

- Validación manual final en navegador de Idonia con resolución de reCAPTCHA.
- Confirmación del PIN oficial vigente del slug `hacknum23` si el actual no es aceptado por la plataforma.
