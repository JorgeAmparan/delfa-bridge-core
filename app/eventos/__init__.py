"""
Persistencia de eventos operativos y observaciones en el DKG (B2 §9).

DOCYAN LDE™ by XCID.

Preparación para el Playbook Nivel A futuro (B7+/B8+) SIN construir lógica de
Playbook todavía: solo asegura que la persistencia mínima ocurre para que B7+
tenga datos sobre los cuales detectar patrones repetidos.

Usa `dkg_client` (importación, no modificación de app/graph — regla §13). La
ontología B1 ya soporta `:EventoOperativo` (tipo="consulta_realizada") y
`:Observacion`.
"""
from app.eventos.persistencia import (
    registrar_consulta_realizada,
    registrar_observacion,
)

__all__ = ["registrar_consulta_realizada", "registrar_observacion"]
