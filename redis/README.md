# docyan-lde-redis — Redis compartido (B2.1)

> **DOCYAN LDE™ by XCID.** 5º proceso de la topología Fly. Un solo Redis,
> self-hosted, con **doble propósito**.

## Doble propósito

1. **Cola de jobs de ingesta (B2).** El backend encola jobs hacia el worker
   `docyan-lde-ingest` (dispatcher Opción A: `LIST` + `BLPOP`). Variable
   `REDIS_QUEUE_URL` en backend y worker.
2. **Session Manager + APScheduler (B4).** Sesiones del Master Orchestrator con
   TTL diferenciado + backend del scheduler (decisión #6 Paso C). Variable
   `REDIS_URL`.

Un único Redis para ambos casos, levantado como **Fly app aparte** por coherencia
con la topología de procesos separados (cada componente escala y se respalda
independiente). `REDIS_QUEUE_URL` y `REDIS_URL` pueden apuntar a esta misma app
(opcionalmente a DBs lógicas distintas, p.ej. `/0` cola, `/1` sesiones).

## Configuración (`redis.conf`)

| Opción | Valor | Por qué |
|---|---|---|
| `appendonly` | `yes` | AOF: cola y sesiones no se pierden en reinicio. |
| `appendfsync` | `everysec` | Balance durabilidad/throughput (~1s de pérdida máx). |
| `maxmemory` | `256mb` | Límite tier alfa. |
| `maxmemory-policy` | `noeviction` | Cola/sesiones NO se evictan en silencio: si se llena, falla explícito. |
| `protected-mode` | `no` | Acceso interno por flycast (no público). |
| `bind` | `0.0.0.0` | Escucha en interfaces internas de Fly. |
| `dir` | `/data` | AOF en el volumen persistente. |

## Operación / deploy (PENDIENTE DE JORGE)

```bash
flyctl apps create docyan-lde-redis
flyctl volumes create redis_data --region dfw --size 5 --app docyan-lde-redis
flyctl deploy --app docyan-lde-redis --dockerfile redis/Dockerfile   # desde la raíz

# Apuntar backend y worker a este Redis (red privada Fly):
flyctl secrets set REDIS_URL="redis://docyan-lde-redis.internal:6379/1" \
  REDIS_QUEUE_URL="redis://docyan-lde-redis.internal:6379/0" --app docyan-lde-api
flyctl secrets set REDIS_QUEUE_URL="redis://docyan-lde-redis.internal:6379/0" \
  --app docyan-lde-ingest
```

Verificación: `flyctl status --app docyan-lde-redis` y, desde un proceso en la red
privada, `redis-cli -h docyan-lde-redis.internal ping` → `PONG`.

## Observación técnica para Jorge (no bloqueante)

`maxmemory 256mb` sobre una VM de 256 MB es ajustado: la reescritura de AOF usa
copy-on-write y el SO necesita headroom, por lo que en carga real Redis podría
acercarse al límite de la VM. Si la cola/sesiones crecen en pilotos, conviene
**subir la VM a 512 MB** (y dejar `maxmemory ~256–384mb`) o bajar `maxmemory` a
~200mb. Se deja como está según el contrato B2.1; queda anotado para ajustar con
datos de uso reales.

## Desarrollo local

En local NO se usa esta app: los tests usan `fakeredis` o el Redis-compatible de
`docyan-lde-graph` (FalkorDB) en `localhost:6379` vía `docker-compose.yml`. Esta
app es solo para producción en Fly.
