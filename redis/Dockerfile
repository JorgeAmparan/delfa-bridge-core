# docyan-lde-redis — Redis compartido (B2.1).
# 5º proceso de la topología DOCYAN. Doble propósito:
#   - Cola de jobs de ingesta (B2, dispatcher Opción A: LIST + BLPOP).
#   - Session Manager (TTL diferenciado) + APScheduler backend (B4, decisión #6).
# Imagen oficial redis:7-alpine (~30 MB). Config en redis.conf.
#
# El build CONTEXT debe ser ESTE directorio (redis/), por dos motivos verificados
# empíricamente (B2.1 2/2):
#   1. El .dockerignore de la RAÍZ excluye todo salvo el backend (`*` + !app...),
#      así que con context=raíz `redis/` no entra al context (deploy mostró
#      "context: 2B" y COPY fallaba con "/redis.conf": not found).
#   2. Con context=redis/, Docker usa (o ignora) el .dockerignore de redis/, no el
#      de la raíz, y `COPY redis.conf` resuelve simple.
# Por eso el deploy se hace DESDE redis/ (ver redis/README.md): el context queda en
# redis/ y la ruta del COPY es relativa a él.
FROM redis:7-alpine

COPY redis.conf /usr/local/etc/redis/redis.conf

EXPOSE 6379

# Arranca con la config explícita (AOF + maxmemory + noeviction). El volumen
# persistente se monta en /data (ver fly.toml [mounts]).
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
