"""
B1 §11.4 / §13 — Backup y restore de FalkorDB funcionan. Test bloqueador.

Round-trip real: crear datos → backup → borrar → restore → verificar que vuelven.
Usa el motor portable `scripts.falkordb_backup` (redis-py DUMP/RESTORE por grafo),
el mismo que invocan backup_falkordb.sh / restore_falkordb.sh.
"""
import json

from scripts import falkordb_backup as fb
from tests.conftest import requires_falkordb


@requires_falkordb
def test_backup_restore_round_trip(dkg, tmp_path):
    tid = "t_backup"
    graph = f"docyan_tenant_{tid}"
    dkg.create_entity(tid, {"token_qr": "QR-BK", "tipo": "bomba"})

    r = fb._redis()
    bundle = fb.backup_bundle([graph], r=r)
    assert bundle["meta"]["graph_count"] == 1
    assert graph in bundle["graphs"]

    # Persistencia a archivo (lo que hace el script) y relectura.
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle))

    # "Borrar datos"
    dkg.drop_tenant_graph(tid)
    assert dkg.query(tid, "MATCH (e:EntidadOperativa) RETURN e") == []

    # Restore desde el bundle en disco.
    restored = fb.restore_bundle(json.loads(path.read_text()), r=r)
    assert restored == 1

    back = dkg.query(tid, "MATCH (e:EntidadOperativa) RETURN e")
    assert len(back) == 1 and back[0]["token_qr"] == "QR-BK"


@requires_falkordb
def test_backup_lists_only_tenant_graphs(dkg):
    tid = "t_backup_list"
    dkg.create_tenant(tid, {"nombre": "L", "tipo": "cliente_final_directo"})
    keys = fb.list_graph_keys()
    assert all(k.startswith("docyan_tenant_") for k in keys)
    assert f"docyan_tenant_{tid}" in keys
