# Checklist final BE/FE/QA para demo

## Objetivo
Validar que MediLink esta listo para una demo de hackathon funcional, limpia y defendible, separando lo que ya esta cerrado de lo que depende de Idonia remoto.

## Backend

### BE-01 Autenticacion y roles
- [x] Login devuelve token JWT y datos de usuario.
- [x] Patients y Doctor estan protegidos por JWT.
- [x] Doctor solo ve sus pacientes asignados.
- [x] Patient solo ve su propio registro.
- [x] Accesos cruzados devuelven 403.

### BE-02 Busqueda clinica
- [x] Existe `GET /api/patients/search`.
- [x] Soporta `name` y `dni`.
- [x] Soporta `page` y `page_size`.
- [x] Tolera mayusculas/minusculas y acentos.
- [x] Devuelve 422 si no se manda `name` o `dni`.

### BE-03 Humanizacion + FHIR
- [x] `POST /api/reports/process` genera humanizacion.
- [x] `POST /api/reports/process` genera FHIR DiagnosticReport.
- [x] `POST /api/reports/process/pdf` genera PDF de informe paciente.
- [x] Fallback local funciona si Recog no esta disponible.

### BE-04 Errores y trazabilidad
- [x] Errores 4xx/5xx usan `{code, message, details, trace_id}`.
- [x] Se expone `x-trace-id` en respuestas.
- [x] OpenAPI documenta errores criticos.

### BE-05 Idonia / Fase II / Fase III
- [x] Se crea artefacto local humanizado canonico en `backend/static/ficheros_reto/humanizados/Informe_para_paciente_PAT-002.txt`.
- [x] El bundle previsto incluye informe tecnico, informe para paciente y estudio.
- [x] La referencia del Magic Link apunta a carpeta de paciente/estudio.
- [x] El backend esta preparado para usar PIN automatico del endpoint de creacion del Magic Link.
- [ ] Tenant Idonia responde 200 en `whoami`.
- [ ] Tenant Idonia permite subida y creacion de Magic Link.

## Frontend

### FE-01 Flujo medico
- [x] Login funcional.
- [x] Dashboard medico con listado de pacientes.
- [x] Busqueda por nombre/DNI integrada.
- [x] Accion clinica rapida desde tarjeta de paciente.
- [x] Procesado de informe visible en UI.
- [x] Export FHIR visible en UI.
- [x] Boton de acceso Idonia en 1 clic integrado.

### FE-02 Flujo paciente
- [x] Dashboard paciente funcional.
- [x] Informe humanizado visible.
- [x] Recetas visibles en lenguaje claro.
- [x] Avatar Elena funcional.
- [x] Feedback del avatar funcional.

### FE-03 Observabilidad UX
- [x] Errores principales muestran mensaje util.
- [x] Errores principales muestran `trace_id` cuando backend lo devuelve.
- [x] Frontend compila con `npm run build`.

## QA

### QA-01 Smoke API
- [x] `GET /api/auth/demo-accounts`
- [x] `POST /api/auth/login`
- [x] `GET /api/patients/`
- [x] `GET /api/patients/search`
- [x] `GET /api/doctor/patients`
- [x] `POST /api/reports/process`
- [x] `POST /api/avatar/chat`
- [x] `GET /api/fhir/metadata`

### QA-02 Seguridad por rol
- [x] 401 sin token en endpoints protegidos.
- [x] 403 en accesos cruzados doctor/patient.
- [x] 200 en accesos permitidos.

### QA-03 Limpieza del proyecto
- [x] Eliminado duplicado legacy de informe humanizado PAT-002.
- [x] Eliminados artefactos de prueba PAT-001 y PAT-003.
- [x] Conservado solo el artefacto canonico de demo PAT-002.

## Veredicto para demo

### Listo para demo local
- [x] Si

### Listo para demo end-to-end con Idonia
- [x] Pendiente de desbloqueo externo del tenant/credenciales/permisos Idonia

## Mensaje ejecutivo
- El proyecto esta listo para demo funcional local completa.
- La unica dependencia pendiente para cierre total end-to-end es la autorizacion del tenant Idonia remoto.
