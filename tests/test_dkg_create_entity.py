"""B1 §13 — Crear :EntidadOperativa con propiedades del doc 01. Test bloqueador."""
import pytest

from tests.conftest import requires_falkordb


@requires_falkordb
def test_create_entity_with_doc01_properties(dkg):
    tid = "t_entity"
    ent = dkg.create_entity(
        tid,
        {
            "token_qr": "QR-COMP-01",
            "tipo": "compresor",
            "sitio": "Planta Juárez",
            "estado_ciclo_vida": "activo",
        },
    )
    assert ent["token_qr"] == "QR-COMP-01"
    assert "id" in ent

    read = dkg.get_entity(tid, ent["id"])
    assert read is not None
    assert read["tipo"] == "compresor"
    assert read["sitio"] == "Planta Juárez"


@requires_falkordb
def test_create_entity_validates_required_token_qr(dkg):
    dkg.track("t_entity_invalid")
    with pytest.raises(Exception):
        # token_qr es obligatorio en la ontología.
        dkg.create_entity("t_entity_invalid", {"tipo": "valvula"})


@requires_falkordb
def test_update_entity_in_place(dkg):
    tid = "t_entity_update"
    ent = dkg.create_entity(tid, {"token_qr": "QR-UPD", "estado_ciclo_vida": "activo"})
    updated = dkg.update_entity(tid, ent["id"], {"estado_ciclo_vida": "baja"})
    assert updated["estado_ciclo_vida"] == "baja"
    assert dkg.get_entity(tid, ent["id"])["estado_ciclo_vida"] == "baja"
