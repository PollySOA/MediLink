# Despliegue en Azure for Students

## Objetivo
Desplegar MediLink de forma viable con una cuenta Azure for Students, separando backend y frontend para minimizar friccion y coste.

## Arquitectura recomendada

1. Backend
- Servicio: Azure App Service (Linux, Python 3.12)
- App: FastAPI + Uvicorn

2. Frontend
- Opcion recomendada: Azure Static Web Apps
- Opcion alternativa: Azure App Service (Node)

## Por que esta opcion
- FastAPI encaja bien en App Service con startup command simple.
- React + Vite se despliega muy bien como sitio estatico.
- Azure for Students suele cubrir este escenario sin complejidad de contenedores.

## Pre-requisitos
- Cuenta Azure for Students activa
- Suscripcion disponible
- Azure CLI instalada y login hecho
- Repo funcionando localmente

## Paso 1 - Backend en App Service

### 1.1 Crear recursos
- Resource Group
- App Service Plan Linux B1 o Free si disponible
- Web App Python 3.12

### 1.2 Variables de entorno necesarias
Configurar en App Service > Environment variables:
- IDONIA_PUBLIC_ID
- IDONIA_API_SECRET
- IDONIA_API_KEY
- IDONIA_BASE_URL
- IDONIA_UPLOAD_TEMPLATE
- IDONIA_STUDIES_TEMPLATE
- IDONIA_MAGIC_LINK_PATH
- IDONIA_MAGIC_LINK_QUERY_PARAM
- IDONIA_MAGIC_LINK_PUBLIC_BASE_URL
- IDONIA_MAGIC_LINK_REFERENCE_MODE
- IDONIA_MAGIC_LINK_PIN
- IDONIA_NUM_PARTICIPANTE
- IDONIA_PATIENT_PASSWORD
- IDONIA_SOURCE_REPORT_PDF_PATH
- IDONIA_SOURCE_STUDY_FILE_PATH
- RECOG_API_URL
- RECOG_API_KEY
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_DEPLOYMENT
- AZURE_OPENAI_API_VERSION
- JWT_SECRET
- APP_ENV=production

### 1.3 Startup command
Usar como startup command:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 1.4 Estructura esperada
El despliegue del backend debe apuntar a la carpeta `backend/`.

### 1.5 Validaciones
- `GET /docs` responde 200
- `POST /api/auth/login` responde 200
- `GET /api/fhir/metadata` responde 200
- `GET /api/reports/idonia/whoami` responde 200 si Idonia esta correctamente autorizado

## Paso 2 - Frontend en Static Web Apps

### 2.1 Build
El frontend ya usa:

```bash
npm run build
```

### 2.2 Variable necesaria
Definir en el frontend:
- `VITE_API_URL=https://<tu-backend>.azurewebsites.net`

### 2.3 Artefacto a publicar
Publicar la carpeta:
- `frontend/dist`

### 2.4 Validaciones
- La app carga
- Login funcional
- Dashboard medico funcional
- Dashboard paciente funcional
- Errores muestran trace_id cuando backend lo devuelve

## Opcion alternativa - Frontend en App Service
Si no usas Static Web Apps:
- Crear App Service Node
- Build command: `npm install && npm run build`
- Publicar `dist` con un servidor estatico o usar SWA es preferible

## Orden recomendado de despliegue
1. Backend
2. Verificar API base
3. Configurar `VITE_API_URL`
4. Frontend
5. Smoke test completo

## Smoke test post-deploy

### Backend
- `GET /`
- `GET /docs`
- `POST /api/auth/login`
- `GET /api/patients/search`
- `GET /api/doctor/patients`
- `POST /api/reports/process`

### Frontend
- Login medico
- Busqueda paciente por nombre/DNI
- Procesado de informe
- Export FHIR
- Boton Idonia
- Login paciente
- Elena chat

## Riesgos conocidos
1. Idonia remoto puede seguir bloqueado si tenant/permisos no estan habilitados.
2. El archivo `backend/.env` no debe desplegarse tal cual; usar variables del App Service.
3. `backend/static/ficheros_reto/Informe_RM_RODILLA.pdf` debe existir en despliegue si Fase I depende del fichero real.

## Recomendacion final
- Para demo hackathon: desplegar primero backend y frontend aunque Idonia siga bloqueado externamente.
- Si Idonia no se desbloquea a tiempo, demostrar:
  - humanizacion
  - FHIR
  - RBAC
  - UX medico/paciente
  - artefacto humanizado local
  - mensaje de soporte y trazabilidad de errores
