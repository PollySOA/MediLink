# Fase II y III - Microtareas sin bloqueos

## Objetivo
Cumplir Fase II (humanizacion + inyeccion en Idonia) y Fase III (Magic Link) sin saltar puntos, con evidencia verificable.

## Estado actual por microtarea

1. [x] MT-01 - Guardar politica de trabajo (ingenieria de prompt, anti-alucinacion, limpieza)
- Evidencia: memoria `/memories/prompt-engineering-policy.md` creada.

2. [x] MT-02 - Verificar pipeline de humanizacion con Recog/fallback
- Evidencia: `backend/services/recog_service.py` usa Recog y fallback demo si no hay config o hay caida de red.

3. [x] MT-03 - Verificar inyeccion en Idonia de bundle completo
- Evidencia: `backend/routers/reports.py` en `_upload_full_bundle` sube:
  - informe tecnico (Fase I)
  - informe para paciente (humanizado)
  - estudio radiologico

4. [x] MT-04 - Verificar generacion de Magic Link por carpeta (seguimiento)
- Evidencia: `backend/routers/reports.py` usa `magic_link_reference = "Traslados desde Asturias/<dni>"` en `create_patient_idonia_link`.

5. [x] MT-05 - Crear artefacto humanizado local auditable
- Evidencia: se persiste `backend/static/ficheros_reto/humanizados/Informe_para_paciente_<PATIENT_ID>.txt`.

6. [x] MT-06 - Garantizar creacion del archivo humanizado aunque Idonia falle
- Evidencia: orden de ejecucion en `_upload_full_bundle` crea archivo local antes de subir a Idonia.

7. [x] MT-07 - Probar Fase II/III en runtime
- Evidencia actual:
  - Fase II local: archivo humanizado creado para `PAT-002`.
  - Fase II/III remoto: Idonia devuelve 401 (credenciales externas), por lo que el endpoint responde 502.

8. [ ] MT-08 - Cerrar bloqueo externo de credenciales Idonia
- Accion requerida: cargar credenciales validas de staging en `.env`.
- Criterio de salida: `POST /api/reports/patients/PAT-002/idonia-link` devuelve 200 con `magic_link_url`.
- Estado actual: probado con las credenciales disponibles y con reinicio completo del backend; Idonia sigue respondiendo `401 unauthorized` en upload y Magic Link, y `500 bad request` en `whoami`.
- Siguiente accion: confirmar con soporte/organizacion que el tenant, permisos y contenedores `report_hak_num23` / `dicom_hak_num23` estan habilitados para estas credenciales.

9. [ ] MT-09 - Revalidar extremo a extremo con credenciales validas
- Checks:
  - `humanized_file_ok`
  - subida bundle Idonia 200
  - magic link 200 y apertura en visor
- Estado actual:
  - `humanized_file_ok`: si, validado localmente.
  - subida bundle Idonia 200: no, bloqueado externamente (actualmente 502 desde backend por 401 remoto).
  - magic link 200 y apertura en visor: no, bloqueado externamente por la misma causa.
- Criterio para cerrar MT-09: repetir la prueba completa inmediatamente despues de que soporte confirme acceso valido en staging.

10. [x] MT-10 - QA final sin residuos
- Revisar archivos generados, limpiar temporales no usados y dejar solo artefactos utiles para demo.
- Resultado: se conserva solo el artefacto canonico de demo `backend/static/ficheros_reto/humanizados/Informe_para_paciente_PAT-002.txt`.

11. [x] MT-10a - Limpiar duplicado legacy del informe humanizado PAT-002
- Evidencia: eliminado `backend/static/ficheros_reto/Informe_para_paciente_PAT-002.txt`; se conserva la version canonica en `backend/static/ficheros_reto/humanizados/Informe_para_paciente_PAT-002.txt`.

## Bloqueo actual (no interno)
- Bloqueo externo: autenticacion Idonia (`401 unauthorized`) desde entorno local.
- Impacto: no se puede completar el tramo remoto de Fase II/III hasta actualizar credenciales.

## Siguiente microtarea inmediata
- Ejecutar MT-08: validar/actualizar credenciales Idonia en entorno y repetir prueba del endpoint de link.
