# DKG — Topología de procesos (B1)

> **DOCYAN LDE™ by XCID.** Decisión arquitectónica central de B1: **4 procesos
> separados desde día 1, no monolítico** (B1 §Contexto). Cada uno escala y se
> respalda independiente.

## Los 4 procesos

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

   ┌────────────────────────────────────────────────────────────────┐
   │ docyan-lde-ingest  (worker de ingesta) — SE CONSTRUYE EN B2.    │
   │ Docling + LlamaIndex + GraphRAG-SDK + LiteLLM. NO existe en B1. │
   └────────────────────────────────────────────────────────────────┘
```

| Proceso | Fly app | Puerto | Público | Persistencia | VM |
|---|---|---|---|---|---|
| Backend | `docyan-lde-api` | 8000 | sí (HTTPS) | stateless | shared-cpu-2x / 1 GB |
| Grafo | `docyan-lde-graph` | 6379 | **no** (.internal) | volumen `/data` (RPO 15m) | shared-cpu-2x / 2 GB |
| Embedder | `docyan-lde-embedder` | 8000 | **no** (.internal) | modelo en imagen | shared-cpu-4x / 4 GB |
| Ingesta (B2) | `docyan-lde-ingest` | — | no | — | — |

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
| backend → embedder | `docyan-lde-embedder.internal:8000` | `EMBEDDER_URL` |

`bge_client` (cliente HTTP puro, sin torch) y `DKGClient` (cliente `falkordb`)
viven en el backend y hablan con los servicios por la red privada de Fly.

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
