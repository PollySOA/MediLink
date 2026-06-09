# MT-08 y MT-09 - Desbloqueo Idonia (operativo)

## Estado
- Backend local: OK.
- Fase II local (archivo humanizado): OK.
- Idonia remoto: bloqueado por autenticacion/permiso (401 upload, whoami 500 bad request).

## MT-08 - Checklist de desbloqueo (entorno)

1. Validar con organizacion Idonia que el API key corresponde al tenant y num_participante correctos.
2. Confirmar que los contenedores existen y son accesibles:
- report_hak_<num_participante>
- dicom_hak_<num_participante>
3. Verificar que el usuario/API key tiene permiso de escritura en esos contenedores.
4. Confirmar base URL de entorno:
- staging: https://connect-staging.idonia.com
5. Confirmar publico visor y slug:
- https://staging.idonia.com/v/<slug>
6. Validar formato de credenciales en .env:
- IDONIA_API_KEY
- IDONIA_NUM_PARTICIPANTE
- IDONIA_UPLOAD_TEMPLATE
- IDONIA_STUDIES_TEMPLATE
- IDONIA_MAGIC_LINK_PATH
- IDONIA_MAGIC_LINK_QUERY_PARAM
- IDONIA_MAGIC_LINK_PUBLIC_BASE_URL

## MT-09 - Verificacion end-to-end

Ejecutar en orden:

1) Whoami
- GET /api/reports/idonia/whoami
- Esperado: 200

2) Bundle + Magic Link
- POST /api/reports/patients/PAT-002/idonia-link?resource=report&include_bundle=true
- Esperado: 200 con magic_link_url y magic_link_route

3) Visor
- Abrir magic_link_url
- Esperado: ver imagen/estudio + informe tecnico + informe para paciente

4) Evidencia local Fase II
- Archivo: backend/static/ficheros_reto/humanizados/Informe_para_paciente_PAT-002.txt
- Esperado: existe y contiene texto humanizado

## MT-10 - Cierre limpieza

1. Revisar que no haya archivos temporales no usados.
2. Mantener solo artefactos utiles de demo.
3. Confirmar build frontend y endpoints criticos backend.
