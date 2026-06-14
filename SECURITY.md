# 🔒 Política de Seguridad MediLink

## Reporte de Vulnerabilidades

Si descubres una vulnerabilidad de seguridad, por favor **NO** la reportes públicamente en GitHub Issues.  
Contacta al equipo directamente para un disclosure responsable.

---

## Configuración Segura

### 1. Variables de Entorno (Backend)

**⚠️ NUNCA commitear** el archivo `backend/.env` al repositorio.

#### Setup Local
```bash
cd backend
cp .env.example .env
# Editar .env con tus credenciales reales
```

#### Variables Críticas de Producción
Estas variables **DEBEN** ser rotadas en producción:

```bash
# JWT Secret (mínimo 32 caracteres aleatorios)
JWT_SECRET=<generar-con-openssl-rand-hex-32>

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=<tu-clave-azure>

# Idonia API
IDONIA_API_KEY=<tu-clave-idonia>
IDONIA_API_SECRET=<tu-secret-idonia>

# Recog API
RECOG_API_KEY=<tu-clave-recog>
RECOG_CLIENT_SECRET=<tu-secret-recog>

# CORS (lista separada por comas)
ALLOWED_ORIGINS=https://your-frontend.azurewebsites.net,https://app.example.com
```

#### Generación de JWT_SECRET Seguro
```bash
# Linux/Mac
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### 2. Frontend (Variables de Build)

El frontend usa variables de entorno en **tiempo de compilación** (no runtime).

#### Desarrollo Local
```bash
cd frontend
npm run dev
# Usa VITE_API_URL por defecto: http://localhost:8000
```

#### Build de Producción
```bash
# Configurar API URL antes de build
export VITE_API_URL=https://your-backend.azurewebsites.net
npm run build
```

**⚠️ IMPORTANTE:** Las variables `VITE_*` se embeben en el bundle JavaScript.  
**NO** incluir secretos, API keys o tokens en variables `VITE_*`.

---

### 3. Deployment Azure

#### App Settings Requeridos (Backend)
Configurar en Azure Portal → App Service → Configuration:

```
APP_ENV=production
JWT_SECRET=<strong-random-secret>
ALLOWED_ORIGINS=https://app-medilink-web-<hash>.azurewebsites.net

# Idonia
IDONIA_PUBLIC_ID=<tu-public-id>
IDONIA_API_SECRET=<tu-secret>
IDONIA_API_KEY=<tu-key>
IDONIA_BASE_URL=https://connect.idonia.com
IDONIA_UPLOAD_TEMPLATE=report_hak_<tu-num>
IDONIA_STUDIES_TEMPLATE=dicom_hak_<tu-num>
IDONIA_NUM_PARTICIPANTE=<tu-num>
IDONIA_PATIENT_PASSWORD=<password-seguro>

# Recog
RECOG_API_URL=https://api.recog.es/relisten/dictation/process/report-results
RECOG_API_KEY=<tu-clave>

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<tu-recurso>.openai.azure.com/
AZURE_OPENAI_API_KEY=<tu-clave>
AZURE_OPENAI_DEPLOYMENT=Phi-3.5-mini-instruct
AZURE_OPENAI_API_VERSION=2024-02-01
```

#### Scripts de Deployment
Los scripts en `scripts/` usan variables de entorno con valores por defecto:

```bash
# Sobrescribir con tus valores de Azure
RESOURCE_GROUP=tu-rg \
WEBAPP_NAME=tu-webapp \
ALLOWED_ORIGINS=https://tu-frontend.com \
  bash scripts/deploy_backend_one_shot.sh
```

**⚠️ Los valores por defecto son específicos del proyecto demo.**  
Para uso en producción, eliminar valores por defecto de los scripts.

---

## Checklist de Seguridad Pre-Deployment

### Backend
- [ ] `.env` no está versionado en Git
- [ ] `JWT_SECRET` generado con al menos 32 caracteres aleatorios
- [ ] `ALLOWED_ORIGINS` configurado con URLs de frontend reales
- [ ] Todas las API keys reemplazadas (no usar valores de `.env.example`)
- [ ] App settings configurados en Azure Portal

### Frontend
- [ ] `VITE_API_URL` apunta al backend correcto
- [ ] No hay secretos en variables `VITE_*`
- [ ] `dist/` no está versionado en Git
- [ ] Build de producción ejecutado con `npm run build`

### Azure
- [ ] CORS configurado correctamente en backend
- [ ] Firewall/NSG configurado (si aplica)
- [ ] HTTPS habilitado en ambas App Services
- [ ] Monitoring y alertas configuradas
- [ ] Backup habilitado para datos críticos

---

## Auditoría de Dependencias

### Frontend (npm)
```bash
cd frontend
npm audit
# Debe mostrar: "0 vulnerabilities"
```

### Backend (Python)
```bash
cd backend
source .venv/bin/activate
pip check
# Debe mostrar: "No broken requirements found"
```

---

## Rotación de Secretos

### Frecuencia Recomendada
- **JWT_SECRET:** Cada 90 días o ante compromiso
- **API Keys externas:** Según política del proveedor (Idonia, Recog, Azure)
- **Contraseñas demo:** Cambiar inmediatamente en producción

### Proceso de Rotación
1. Generar nuevo secreto
2. Actualizar App Settings en Azure
3. Reiniciar App Service
4. Validar funcionamiento con smoke tests
5. Invalidar secreto anterior en proveedor

---

## CORS y Seguridad de Origen

### Configuración Actual
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,  # De variable ALLOWED_ORIGINS
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Mejores Prácticas
- **Desarrollo:** Usar `localhost` y `127.0.0.1` con puertos específicos
- **Producción:** Listar URLs exactas en `ALLOWED_ORIGINS`
- **NO usar** `allow_origins=["*"]` con `allow_credentials=True`

---

## Contacto de Seguridad

Para reportar vulnerabilidades o consultas de seguridad:
- **Email:** [Configurar email del equipo]
- **Tiempo de respuesta:** 48 horas hábiles
- **PGP Key:** [Opcional: publicar clave PGP]

---

## Historial de Auditorías

| Fecha      | Tipo        | Estado | Vulnerabilidades |
|------------|-------------|--------|------------------|
| 2026-06-14 | Completa    | ✅ PASS | 0 críticas       |
| -          | -           | -      | -                |

**Última auditoría:** 2026-06-14  
**Próxima auditoría:** [Definir calendario]

---

## Referencias

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Azure Security Best Practices](https://docs.microsoft.com/en-us/azure/security/fundamentals/best-practices-and-patterns)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
