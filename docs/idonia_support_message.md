# Mensaje para soporte de Idonia

Hola,

Estamos integrando MediLink para el hackathon y necesitamos validar acceso sobre vuestro entorno staging.

## Configuracion que estamos usando
- Base URL: https://connect-staging.idonia.com
- Endpoint informes: report_hak_num23
- Endpoint estudios: dicom_hak_num23
- URL visor / Magic Link: https://staging.idonia.com/v/hacknum23
- Query param Magic Link: route

## Credenciales configuradas
- Las credenciales exactas se enviaran por canal seguro o ya estan cargadas en el entorno local.
- No incluimos Public ID ni API Secret en este documento para evitar exponer secretos en repositorio o documentacion compartida.

## Comportamiento esperado
1. Subir a Idonia un bundle con:
- informe tecnico
- informe humanizado para paciente
- estudio radiologico
2. Generar un Magic Link por carpeta de paciente/estudio.
3. Usar el PIN devuelto automaticamente por el endpoint de creacion del Magic Link.

## Error real observado
Pruebas repetidas tras reinicio completo del backend para asegurar recarga de configuracion.

### 1) Whoami
- Endpoint: GET /whoami
- Resultado desde nuestro backend: 502
- Respuesta remota encapsulada: 500 bad request
- Mensaje remoto: "no rows in result set"
- Trace ID backend mas reciente: `efc0df16a384415babf52cfef3c67a3e` para upload y `657fd7a244aa4282a85cc184c6d7fa7d` para Magic Link.

### 2) Subida de archivo
- Endpoint remoto usado: POST /files/report_hak_num23
- Resultado desde nuestro backend: 502
- Respuesta remota encapsulada: 401 unauthorized
- Mensaje remoto: "no rows in result set"

### 3) Creacion de Magic Link
- Endpoint remoto usado: PUT /ml?route=Traslados%20desde%20Asturias%2FD210105597
- Resultado desde nuestro backend: 502
- Respuesta remota encapsulada: 401 unauthorized
- Mensaje remoto: "no rows in result set"

## Lo que necesitamos confirmar
1. Que las credenciales cargadas en el entorno pertenecen realmente al tenant/participante correcto para `num23`.
2. Que tienen permisos de escritura sobre:
- report_hak_num23
- dicom_hak_num23
3. Que el slug `hacknum23` esta asociado al mismo tenant y entorno staging.
4. Que el flujo correcto de acceso al visor es mediante el PIN devuelto por la creacion del Magic Link.
5. Si hay algun requisito adicional para `whoami`, subida de archivos o creacion de Magic Link en este tenant.

## Estado de nuestra integracion
- El backend ya esta alineado para consumir el PIN automatico del Magic Link.
- El flujo local de humanizacion y generacion de artefacto para paciente funciona correctamente.
- El unico bloqueo restante es la autorizacion/resolucion del tenant Idonia remoto.

Si os viene mejor, podemos reenviaros tambien los `trace_id` de las ultimas respuestas de error observadas desde nuestro backend.

Gracias.
