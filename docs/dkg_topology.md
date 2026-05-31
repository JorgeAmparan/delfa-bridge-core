# DKG — Topología de procesos (B1 + B2/B2.1)

> **DOCYAN LDE™ by XCID.** Decisión arquitectónica central de B1: **procesos
> separados desde día 1, no monolítico** (B1 §Contexto). Cada uno escala y se
> respalda independiente. Hoy son **5 procesos** (B2 agregó el worker de ingesta;
> B2.1 agregó el Redis compartido).

## Los 5 procesos

```
                       Internet (público, HTTPS)
                                │
                                ▼
          ┌──────────────────────────────────────────┐
          │  docyan-lde-api      (Fly · dfw · 8000)    │  ← backend FastAPI
          │  consultas · MO · clasificador · admin     │     imagen <1 GB
          └───────┬───────────────────────┬────────────┘
                  │ red privada Fly        │ red privada Fly
                  │ (.internal/.flycast)   │
                  ▼                        ▼
   ┌──────────────────────────┐   ┌────────────────────────────────┐
   │ docyan-lde-graph         │   │ docyan-lde-embedder            │
   │ FalkorDB (dfw · 6379)    │   │ BGE-M3 (dfw · 8000)            │
   │ volumen /data · RPO 15m  │   │ torch+sentence-transformers    │
   │ shared-cpu-2x / 2 GB     │   │ shared-cpu-4x / 4 GB · sin vol │
   └──────────────────────────┘   └────────────────────────────────┘

   ┌────────────────────────────────────┐  ┌──────────────────────────────┐
   │ docyan-lde-ingest (worker, B2)     │  │ docyan-lde-redis (B2.1)      │
   │ Docling + GraphRAG-SDK + LiteLLM + │◄─┤ Redis 7-alpine · 6379        │
   │ PyTorch CPU. flycast · 8000.       │  │ cola ingesta + sesiones MO   │
   │ Consume la cola Redis tras cotizar.│  │ AOF · noeviction · vol /data │
   └────────────────────────────────────┘  └──────────────────────────────┘
            backend ──encola jobs──►  docyan-lde-redis  ◄──BLPOP── worker
```

| Proceso | Fly app | Puerto | Público | Persistencia | VM |
|---|---|---|---|---|---|
| Backend | `docyan-lde-api` | 8000 | sí (HTTPS) | stateless | shared-cpu-2x / 1 GB |
| Grafo | `docyan-lde-graph` | 6379 | **no** (.internal) | volumen `/data` (RPO 15m) | shared-cpu-2x / 2 GB |
| Embedder | `docyan-lde-embedder` | 8000 | **no** (.flycast) | modelo en imagen | shared-cpu-4x / 8 GB |
| Ingesta | `docyan-lde-ingest` | 8000 | **no** (.flycast) | stateless | shared-cpu-4x / 4 GB |
| Redis | `docyan-lde-redis` | 6379 | **no** (.flycast) | volumen `/data` (AOF) | shared-cpu-1x / 256 MB |

Son **5 procesos** (B1 levantó 3; B2 agregó `docyan-lde-ingest`; B2.1 agregó
`docyan-lde-redis`). El worker (B2) consume jobs de la **cola Redis** (decisión
§8 = Opción A): el backend cotiza → encola tras confirmación → el worker procesa
(Docling → GraphRAG-SDK → BGE-M3 → dedup → finalize) y escribe al grafo del
tenant. **`docyan-lde-redis` es compartido** (B2.1): la misma app sirve la cola de
ingesta (`REDIS_QUEUE_URL`) y, desde B4, el Session Manager + APScheduler
(`REDIS_URL`, decisión #6). Detalle en [`worker_architecture.md`](worker_architecture.md),
[`cotizador.md`](cotizador.md) y [`../redis/README.md`](../redis/README.md). **Todo
job de ingesta pasa por el cotizador — no hay bypass.**

## Por qué separados (B1 §Contexto)

- **(a)** La imagen del backend se mantiene **<1 GB** (evita el bloqueo de unpack
  de Fly que B0.5 resolvió). GraphRAG-SDK + Docling + torch NO entran al backend.
- **(b)** BGE-M3 arrastra PyTorch + sentence-transformers (~3 GB) → proceso aparte.
- **(c)** FalkorDB necesita volumen persistente y RPO 15 min (#12): perfil distinto
  al backend stateless.
- **(d)** Escalado independiente por componente según carga.

## Rutas de comunicación

| Origen → Destino | DNS interno | Variable |
|---|---|---|
| backend → grafo | `docyan-lde-graph.internal:6379` | `FALKOR_HOST`, `FALKOR_PORT` |
| backend → embedder | `docyan-lde-embedder.flycast:8000` | `EMBEDDER_URL` |

`bge_client` (cliente HTTP puro, sin torch) y `DKGClient` (cliente `falkordb`)
viven en el backend y hablan con los servicios por la red privada de Fly.

**Lecciones de despliegue (B1, verdad operacional):**

- **Embedder vía `.flycast`, no `.internal`.** El servicio escucha en `0.0.0.0`
  (IPv4); las conexiones directas `.internal` resuelven a la IPv6 6PN y eran
  rechazadas. Bindear `::` (IPv6-only en este kernel) rompía el health-check TCP
  de Fly (IPv4) → la máquina se reiniciaba a media carga del modelo. `.flycast`
  (fly-proxy mediado) puentea IPv4↔IPv6 y es el patrón correcto servicio↔servicio.
- **8 GB de RAM, no 4.** BGE-M3 fp32 (~2.3 GB) + torch satura 4 GB. Optimización
  futura (B2): fp16/int8.
- **Modo offline** (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`): el modelo va
  baked en la imagen; sin offline, `huggingface_hub` contacta huggingface.co y se
  cuelga.
- **Cold-start del modelo ~107 s de carga + ~39 s del primer encode** (CPU);
  una vez caliente, ~0.6 s/consulta. Por eso `min_machines_running=1` (siempre
  encendido) y `BGE_M3_TIMEOUT=120` en el backend. Optimización futura: precargar
  el modelo en el `startup` event en un threadpool.

## Conflicto de dependencias documentado (B1 §9.2)

`graphrag-sdk==1.1.1` (vía `gliner`) fuerza `transformers<5.2.0` y `typer<0.26`,
**incompatibles con Docling** en el mismo entorno. Por eso GraphRAG-SDK + LiteLLM
+ Docling viven en `docyan-lde-ingest` (B2), NO en el backend. El backend solo
usa el cliente `falkordb` (ligero). Resuelto por la topología, no por pins.

## Verificación (B1 §14)

```bash
flyctl apps list                              # api, graph, embedder running
flyctl status --app docyan-lde-graph          # máquina + volumen montado
flyctl status --app docyan-lde-embedder       # máquina respondiendo health

# desde el backend (rol admin):
curl -X POST https://<api>/admin/tenants/test   -H "X-API-Key: <key>"
curl -X POST https://<api>/admin/embedding/test -H "X-API-Key: <key>"  # dim=1024
```

## Backup / restore (B1 §11)

Motor portable [`scripts/falkordb_backup.py`](../scripts/falkordb_backup.py)
(redis-py DUMP/RESTORE por grafo) + wrappers `scripts/backup_falkordb.sh` /
`restore_falkordb.sh`. Almacenamiento externo: **Supabase Storage** (cero vendor
nuevo). Retención 7a prod / 3a operativo (#12). Cron cada 15 min: B6 (o
APScheduler, decisión #3).

## Desarrollo local

`docker-compose.yml` levanta `docyan-graph` (FalkorDB, mismo digest que Fly) y
`docyan-embedder` (BGE-M3). Los tests de integración del DKG corren contra ese
FalkorDB; en CI hay un servicio FalkorDB equivalente (`.github/workflows/ci.yml`).
