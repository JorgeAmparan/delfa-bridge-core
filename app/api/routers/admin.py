"""
Router admin — verificación operativa de la infraestructura DKG (B1 §14).

DOCYAN LDE™ by XCID.

Endpoints administrativos (rol `admin`) que prueban en CALIENTE, desde el
backend en producción, que los dos procesos nuevos de B1 responden:

  POST /admin/tenants/test    → crea un :Tenant de prueba en FalkorDB y lo lee.
  POST /admin/embedding/test  → pide un embedding "hola" al servicio BGE-M3.
  GET  /admin/dkg/health      → PING a FalkorDB.

Multi-tenancy: el tenant de prueba se aísla bajo el `org_id` del admin logueado
(`<org_id>__selftest`), nunca toca grafos de otros tenants (regla absoluta §7).
"""
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import requiere_rol
from app.embeddings.bge_client import bge_client
from app.graph.dkg_client import dkg_client
from app.graph.schemas.dkg_ontology import graph_name_for

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dkg/health")
async def dkg_health(ctx: dict = Depends(requiere_rol("admin"))):
    """PING a FalkorDB (docyan-lde-graph)."""
    ok = dkg_client.health()
    if not ok:
        raise HTTPException(status_code=503, detail="FalkorDB (docyan-lde-graph) no responde.")
    return {"status": "healthy", "component": "docyan-lde-graph"}


@router.post("/tenants/test")
async def tenants_test(ctx: dict = Depends(requiere_rol("admin"))):
    """
    Crea un :Tenant de prueba en el grafo aislado del org y lo lee de vuelta.
    Idempotente: limpia el grafo de autotest antes de crear.
    """
    org_id = ctx["org_id"]
    test_tenant = f"{org_id}__selftest"
    try:
        dkg_client.drop_tenant_graph(test_tenant)
        created = dkg_client.create_tenant(
            test_tenant,
            {"nombre": f"selftest-{org_id}", "tipo": "cliente_final_directo"},
        )
        readback = dkg_client.get_tenant(test_tenant)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"DKG no disponible: {type(exc).__name__}: {exc}")
    return {
        "ok": readback is not None,
        "graph_name": graph_name_for(test_tenant),
        "tenant_id": test_tenant,
        "created_id": created.get("id"),
        "tenant": {k: v for k, v in (readback or {}).items() if not k.startswith("_")},
    }


@router.post("/embedding/test")
async def embedding_test(ctx: dict = Depends(requiere_rol("admin"))):
    """
    Pide un embedding del texto 'hola' al servicio BGE-M3 (docyan-lde-embedder)
    y verifica que la dimensión sea 1024 (BGE-M3) y NO 1536 (OpenAI).
    """
    try:
        vectors = bge_client.get_embeddings(["hola"])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"Embedder (docyan-lde-embedder) no disponible: {type(exc).__name__}: {exc}",
        )
    vector = vectors[0]
    dim = len(vector)
    return {
        "ok": dim == 1024,
        "dim": dim,
        "expected_dim": 1024,
        "model": "BAAI/bge-m3",
        "sample": vector[:5],
    }
