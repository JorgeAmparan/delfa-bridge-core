# docyan-lde-redis — Redis compartido (B2.1).
# 5º proceso de la topología DOCYAN. Doble propósito:
#   - Cola de jobs de ingesta (B2, dispatcher Opción A: LIST + BLPOP).
#   - Session Manager (TTL diferenciado) + APScheduler backend (B4, decisión #6).
# Imagen oficial redis:7-alpine (~30 MB). Config en redis.conf.
#
# El build CONTEXT debe ser ESTE directorio (redis/), verificado empíricamente
# (B2.1 2/2 + B2.2): con `flyctl deploy --config redis/fly.toml` DESDE LA RAÍZ, el
# context queda en la raíz, donde NO existe `redis.conf` (está en redis/redis.conf)
# → `COPY redis.conf` falla con "/redis.conf": not found. Desplegando DESDE redis/
# el context es redis/ y `COPY redis.conf` resuelve. (El .dockerignore de la raíz
# NO es la causa: solo excluye venv/ .env __pycache__/ *.pyc .DS_Store data/ .git/
# *.log; no recorta redis/.) Ver redis/README.md.
FROM redis:7-alpine

COPY redis.conf /usr/local/etc/redis/redis.conf

EXPOSE 6379

# Arranca con la config explícita (AOF + maxmemory + noeviction). El volumen
# persistente se monta en /data (ver fly.toml [mounts]).
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
