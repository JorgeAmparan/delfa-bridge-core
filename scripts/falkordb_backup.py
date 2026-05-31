"""
Motor de respaldo/restauración de FalkorDB (docyan-lde-graph). DOCYAN LDE™ — B1 §11.

Diseño portable: usa el primitivo Redis DUMP/RESTORE a nivel de clave de grafo.
En FalkorDB cada grafo (`graph_name`) es UNA clave Redis serializable con DUMP y
recreable con RESTORE — sin acceso al filesystem de la máquina, sin `redis-cli`,
solo `redis-py` (que YA está en la imagen del backend). Esto lo hace:
  - portable (corre desde el backend Fly o un cron APScheduler — decisión #3),
  - testeable (round-trip real backup→borrar→restore→verificar),
  - multi-tenant-aware (respalda cada grafo `docyan_tenant_*` por separado).

Almacenamiento externo: Supabase Storage (B1 §11.1 — cero vendor nuevo, reusa
SUPABASE_SERVICE_KEY; retención por lifecycle del bucket, 7a/3a #12).

El respaldo es un bundle JSON: {graph_name: base64(dump_blob)} + metadata. La
restauración recrea cada grafo con RESTORE (REPLACE).

CLI:
    python -m scripts.falkordb_backup backup  --out /tmp/bundle.json [--upload]
    python -m scripts.falkordb_backup restore --in  /tmp/bundle.json
    python -m scripts.falkordb_backup restore --download <TS>
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime, timezone

from app.graph.schemas.dkg_ontology import GRAPH_NAME_PREFIX

FALKOR_HOST = os.getenv("FALKOR_HOST") or os.getenv("FALKORDB_HOST", "localhost")
FALKOR_PORT = int(os.getenv("FALKOR_PORT") or os.getenv("FALKORDB_PORT", "6379"))
BACKUP_BUCKET = os.getenv("BACKUP_BUCKET", "falkordb-backups")


def _redis():
    import redis

    return redis.Redis(host=FALKOR_HOST, port=FALKOR_PORT)


def list_graph_keys(r=None, prefix: str = GRAPH_NAME_PREFIX) -> list[str]:
    """Lista las claves de grafo de tenants (docyan_tenant_*)."""
    r = r or _redis()
    keys = []
    for k in r.scan_iter(match=f"{prefix}*"):
        name = k.decode() if isinstance(k, bytes) else k
        keys.append(name)
    return sorted(keys)


def backup_bundle(graph_names: list[str] | None = None, r=None) -> dict:
    """
    Construye un bundle de respaldo {meta, graphs:{name: base64(dump)}}.
    Si graph_names es None, respalda todos los grafos de tenant.
    """
    r = r or _redis()
    names = graph_names if graph_names is not None else list_graph_keys(r)
    graphs: dict[str, str] = {}
    for name in names:
        blob = r.dump(name)
        if blob is None:
            continue  # grafo inexistente / vacío
        graphs[name] = base64.b64encode(blob).decode("ascii")
    return {
        "meta": {
            "product": "DOCYAN LDE",
            "component": "docyan-lde-graph",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "graph_count": len(graphs),
            "format": "redis-dump-base64-v1",
        },
        "graphs": graphs,
    }


def restore_bundle(bundle: dict, r=None, replace: bool = True) -> int:
    """Restaura cada grafo del bundle con RESTORE. Devuelve cuántos restauró."""
    r = r or _redis()
    restored = 0
    for name, b64 in bundle.get("graphs", {}).items():
        blob = base64.b64decode(b64)
        if replace:
            try:
                r.delete(name)
            except Exception:  # noqa: BLE001
                pass
        r.restore(name, 0, blob, replace=True)
        restored += 1
    return restored


# ── Supabase Storage (upload/download) ───────────────────────────────────────


def _supabase_object_url(object_name: str) -> str:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    return f"{base}/storage/v1/object/{BACKUP_BUCKET}/{object_name}"


def upload(object_name: str, data: bytes) -> int:
    import httpx

    key = os.environ["SUPABASE_SERVICE_KEY"]
    resp = httpx.post(
        _supabase_object_url(object_name),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "x-upsert": "true",
        },
        content=data,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.status_code


def download(object_name: str) -> bytes:
    import httpx

    key = os.environ["SUPABASE_SERVICE_KEY"]
    resp = httpx.get(
        _supabase_object_url(object_name),
        headers={"Authorization": f"Bearer {key}"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


def _main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Backup/restore FalkorDB (DOCYAN B1 §11).")
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("backup")
    pb.add_argument("--out", required=True)
    pb.add_argument("--upload", action="store_true")

    pr = sub.add_parser("restore")
    g = pr.add_mutually_exclusive_group(required=True)
    g.add_argument("--in", dest="infile")
    g.add_argument("--download", dest="ts")

    args = p.parse_args(argv)

    if args.cmd == "backup":
        bundle = backup_bundle()
        data = json.dumps(bundle).encode("utf-8")
        with open(args.out, "wb") as fh:
            fh.write(data)
        print(f"[backup] {bundle['meta']['graph_count']} grafos → {args.out} ({len(data)} bytes)")
        if args.upload:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            obj = f"docyan-falkordb-{ts}.json"
            code = upload(obj, data)
            print(f"[backup] subido a Supabase: {BACKUP_BUCKET}/{obj} (HTTP {code})")
        return 0

    if args.cmd == "restore":
        if args.ts:
            obj = f"docyan-falkordb-{args.ts}.json"
            data = download(obj)
        else:
            with open(args.infile, "rb") as fh:
                data = fh.read()
        bundle = json.loads(data)
        n = restore_bundle(bundle)
        print(f"[restore] {n} grafos restaurados.")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
