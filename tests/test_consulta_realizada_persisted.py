"""
B2 §10 / §9 — test bloqueador: al servir una consulta, un :EventoOperativo con
tipo="consulta_realizada" queda persistido en el grafo del tenant; y una
:Observacion se persiste vinculada a su entidad.

Requiere FalkorDB (usa el fixture `dkg`). Se SKIPEA si no está.
"""

from tests.conftest import requires_falkordb


@requires_falkordb
def test_consulta_realizada_se_persiste(dkg):
    from app.eventos import registrar_consulta_realizada

    tenant = "test_consulta_tenant"
    dkg.track(tenant)

    registrar_consulta_realizada(
        tenant_id=tenant,
        usuario_id="user-123",
        consulta_texto="¿Cuál es el par de apriete del seccionador?",
        respuesta_resumen="El par de apriete es 40 Nm según la sección 5.",
        client=dkg,
    )

    rows = dkg.query(
        tenant,
        "MATCH (e:EventoOperativo {tipo: 'consulta_realizada'}) "
        "RETURN e.consulta_texto AS q, e.usuario_id AS u, e.timestamp AS t",
    )
    assert len(rows) == 1
    assert rows[0]["u"] == "user-123"
    assert "seccionador" in rows[0]["q"]
    assert rows[0]["t"]  # timestamp presente


@requires_falkordb
def test_observacion_se_persiste_vinculada_a_entidad(dkg):
    from app.eventos import registrar_observacion

    tenant = "test_obs_tenant"
    dkg.track(tenant)

    # Crea una entidad operativa a la cual anclar la observación.
    entidad = dkg.create_entity(tenant, {"token_qr": "QR-001", "tipo": "equipo"})
    entidad_id = entidad["id"]

    obs = registrar_observacion(
        tenant_id=tenant,
        entidad_id=entidad_id,
        texto="El equipo presentó ruido anómalo durante la operación.",
        autor_id="user-9",
        client=dkg,
    )
    assert obs.get("id")

    # La observación existe y está vinculada a la entidad.
    rows = dkg.query(
        tenant,
        "MATCH (e:EntidadOperativa {id: $eid})-[:TIENE_OBSERVACION]->(o:Observacion) "
        "RETURN o.texto AS texto, o.autor_id AS autor",
        {"eid": entidad_id},
    )
    assert len(rows) == 1
    assert rows[0]["autor"] == "user-9"
    assert "ruido" in rows[0]["texto"]
