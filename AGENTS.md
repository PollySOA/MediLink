# AGENTS.md

## Objetivo de este repositorio
MediLink es una app demo de interoperabilidad y humanizacion medica con backend FastAPI y frontend React+TypeScript.
Contexto funcional y setup base en README: [README.md](README.md).

## Arranque rapido local
- Backend:
  - cd backend
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt
  - cp .env.example .env
  - uvicorn main:app --reload --port 8000
- Frontend:
  - cd frontend
  - npm install
  - npm run dev

## Arquitectura y limites
- Backend en backend: routers, services, models, data, prompts.
- Frontend en frontend/src: pages, components, context, hooks, services.
- Contratos API y modelos tipados en backend/models/schemas.py y frontend/src/types.ts.
- Cambios de contrato entre backend/frontend deben aplicarse en ambos lados dentro del mismo cambio.

## Convenciones para agentes
- Mantener cambios pequenos y focalizados; no reformatear codigo no relacionado.
- En backend, respetar modelos Pydantic y errores tipados (ServiceError) para respuestas HTTP coherentes.
- En frontend, respetar tipado TypeScript estricto y flujo de AuthContext.
- Para prompts LLM, mantener salida estructurada y parseable; no mezclar formatos libres con JSON cuando el endpoint espera JSON.

## Zona sensible: Avatar Elena
Si una tarea toca Avatar Elena, revisar y mantener consistencia entre:
- backend/prompts/medical_prompts.py
- backend/services/azure_llm_service.py
- backend/models/schemas.py
- backend/routers/avatar.py
- frontend/src/types.ts
- frontend/src/pages/PatientDashboard.tsx

Checklist minimo en cambios de Avatar:
1. El prompt del sistema y el parser de salida usan el mismo esquema JSON.
2. El schema Pydantic coincide con la salida real del servicio.
3. El tipo TypeScript coincide con la respuesta backend.
4. El fallback local en backend no rompe el mismo contrato.
5. El flujo de UI de chat no asume claves obsoletas.

## Validacion recomendada antes de cerrar cambios
- Backend: levantar FastAPI y probar /docs.
- Frontend: npm run build para validar tipos y bundle.
- Prueba manual del chat de Avatar (greeting + 1 mensaje usuario).

## No duplicar documentacion
Para detalles de producto, cuentas demo, Azure y consideraciones eticas, enlazar README en lugar de copiar contenido: [README.md](README.md).
