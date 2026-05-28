# DOCYAN LDE — Guía de despliegue

**by XCID SA de CV** — Actualizado 28 mayo 2026

Arquitectura de despliegue: **backend en Fly.io**, **frontend en Vercel**, **FalkorDB y Redis** como servicios. Railway fue retirado.

---

## 1. Backend — Fly.io

**App:** `docyan-lde-api` · **Región primaria:** `mia` (Miami, cercana al corredor T-MEC).

### Prerrequisitos
- `flyctl` instalado y autenticado (`fly auth login`).
- `Dockerfile` del repo (usa `requirements.docker.txt`, sin paquetes macOS-only).
- PyTorch CPU-only se instala en el Dockerfile **antes** de `requirements.docker.txt`:
  ```dockerfile
  RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
  RUN pip install -r requirements.docker.txt
  ```
- Binarios externos de Pista B (B5) instalados en el Dockerfile vía apt/git: `vecalign`, `hunalign`.

### Variables de entorno (secrets Fly.io)
```bash
fly secrets set \
  GEMINI_API_KEY=...        # Gemini 2.5 Flash (extracción + resolution + clasificador). NO GOOGLE_API_KEY.
  OPENAI_API_KEY=...        # gpt-4o-mini = QA del pipeline de ingesta.
  ANTHROPIC_API_KEY=...     # Claude Sonnet 4.6 (traducción Pista A vía MR).
  JWT_SECRET=...            # robusto, sin default inseguro.
  SUPABASE_URL=...          \
  SUPABASE_KEY=...          \
  FALKORDB_URL=...          \
  REDIS_URL=...             \
  Dialog360_API_KEY=...     # WhatsApp BSP (B9).
```
> El `GEMINI_API_KEY` debe usarse con el prefijo `gemini/` en los model strings de LiteLLM, o LiteLLM defaultea a Vertex AI y falla pidiendo credenciales GCP.

### Despliegue
```bash
fly deploy
fly status            # verificar health 200 en docyan-lde-api
fly logs              # monitoreo
```

### FalkorDB y Redis
- **FalkorDB:** instancia dedicada (Fly.io app propia o servicio gestionado). Persiste DKG + DTM + eventos FAT críticos. Respaldo según decisión #12 (RPO 15min, RTO 4h, retención 7 años producción / 3 años operativo) vía `scripts/backup_falkordb.sh`.
- **Redis:** sesiones del Master Orchestrator (TTLs: consulta 30min, troubleshooting 2h, revisión 8h, onboarding 30 días) + backend de APScheduler.

### BGE-M3 self-hosted
Embedder servido localmente (cliente `app/embeddings/bge_client.py`). Requiere torch/transformers en el contenedor. Evaluar en B13 si conviene servicio separado para optimizar el contenedor principal; no eliminar torch a ciegas.

---

## 2. Frontend — Vercel

**Framework:** Next.js 15 App Router. Configuración en `vercel.json`.

### Variables de entorno (Vercel)
```
NEXT_PUBLIC_API_URL=https://docyan-lde-api.fly.dev
```

### Despliegue
- Conectar el repo `docyan-lde-core` a Vercel, root del proyecto = `frontend/`.
- Build: `npm run build`. Output: `.next`.
- Los tipos TypeScript de la API se generan desde el OpenAPI del backend (`frontend/scripts/generate-types.sh`) en el pipeline de build/CI.

---

## 3. Base de datos — Supabase

- Migraciones en `migrations/` (`001`–`008+`), aplicadas en orden.
- RLS multi-tenant donde aplique (consistente con `001`).
- Tablas: `tenants`, `documents`, `entities`, `audit_trail` (+ hash chain), `governance_rules`, `quarantine`, `api_keys`, y las del FAT de alta frecuencia (modelo híbrido FalkorDB+Supabase).

---

## 4. CI/CD — GitHub Actions

- Workflow ejecuta en cada PR: tests backend (pytest), tests frontend (Vitest + Playwright), lint, verificación de secrets (gitleaks).
- Sin tests verdes no se despliega.
- Verificador de integridad de la cadena FAT corre en CI (B6).

---

## 5. Checklist de despliegue inicial

- [ ] `fly secrets` completos (incluido prefijo correcto de Gemini).
- [ ] FalkorDB y Redis accesibles desde la app.
- [ ] Migraciones aplicadas.
- [ ] `fly deploy` con health 200.
- [ ] Frontend en Vercel apuntando a la API.
- [ ] CI verde en el último PR.
- [ ] Backup de FalkorDB programado.
- [ ] Sin `railway.toml` ni referencias a Railway en el repo.

---

© XCID SA de CV — DOCYAN LDE™
