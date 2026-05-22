# Deployment — Panohayan DLE

## Backend (Fly.io)

### First-time setup

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Create app (already configured in fly.toml)
fly apps create panohayan-dle-api

# Set secrets
fly secrets set \
  JWT_SECRET="$(openssl rand -hex 32)" \
  ALLOWED_ORIGINS="https://app.panohayan.com" \
  SUPABASE_URL="https://your-project.supabase.co" \
  SUPABASE_KEY="your-anon-key" \
  SUPABASE_SERVICE_KEY="your-service-key" \
  GOOGLE_API_KEY="your-key" \
  BGE_M3_URL="http://bge-m3.internal:8080" \
  REDIS_URL="redis://redis.internal:6379/0" \
  FALKORDB_HOST="falkordb.internal" \
  ORG_ID="your-org-id"
```

### Deploy

```bash
fly deploy
```

### Verify

```bash
curl https://panohayan-dle-api.fly.dev/health
```

### Rollback

```bash
fly releases
fly deploy --image registry.fly.io/panohayan-dle-api:v<N>
```

## Frontend (Vercel)

### Setup

1. Connect repo to Vercel via GitHub integration.
2. Set root directory to `frontend/` (when frontend exists).
3. Set environment variables in Vercel dashboard:
   - `NEXT_PUBLIC_API_URL=https://panohayan-dle-api.fly.dev`

### Deploy

Automatic on push to `main`.

### Rollback

Use Vercel dashboard > Deployments > select previous > Promote to Production.

## FalkorDB (Fly.io)

```bash
fly apps create panohayan-falkordb
fly volumes create falkordb_data --region mia --size 10
fly deploy --config fly.falkordb.toml
```

## Redis (Fly.io)

```bash
fly apps create panohayan-redis
fly volumes create redis_data --region mia --size 1
fly deploy --config fly.redis.toml
```

## BGE-M3 Embedding Service (Fly.io)

```bash
fly apps create panohayan-bge-m3
fly deploy --config fly.bge.toml
```

Container runs the BGE-M3 model and exposes `/embed`, `/embed_batch`, `/health` on port 8080.

## Maintaining requirements.docker.txt

`requirements.docker.txt` is maintained manually (not auto-generated from `pyproject.toml`). It is a curated subset of `requirements.txt` that excludes macOS-only packages (`pyobjc`, `ocrmac`), platform-specific builds (`torch`, `pyodbc`, `cryptography`), and adds Docker-specific deps (`falkordb`, `redis`).

To detect drift after updating `requirements.txt`:

```bash
./scripts/sync-docker-reqs.sh > /tmp/docker-reqs-candidate.txt
diff requirements.docker.txt /tmp/docker-reqs-candidate.txt
```

Review the diff manually, then update `requirements.docker.txt` as needed. The script strips known macOS packages but does not pin versions — you must verify version pins match.
