# docyan-lde-redis — Redis compartido (B2.1).
# 5º proceso de la topología DOCYAN. Doble propósito:
#   - Cola de jobs de ingesta (B2, dispatcher Opción A: LIST + BLPOP).
#   - Session Manager (TTL diferenciado) + APScheduler backend (B4, decisión #6).
# Imagen oficial redis:7-alpine (~32 MB). Config en redis.conf (montado en build).
FROM redis:7-alpine

COPY redis.conf /usr/local/etc/redis/redis.conf

EXPOSE 6379

# Arranca con la config explícita (AOF + maxmemory + noeviction). El volumen
# persistente se monta en /data (ver fly.toml [mounts]).
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
