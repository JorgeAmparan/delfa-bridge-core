"""
Representación SDK-agnóstica de un schema documental (B2 §6).

DOCYAN LDE™ by XCID.

`DocumentSchema` describe en código QUÉ extraer de un tipo de documento:
entidades, relaciones, prompt de extracción y mapeo a tipos de intención de
visualización (catálogo de 11, para B9/B5). Es independiente de GraphRAG-SDK; el
método `to_sdk_schema()` construye un `graphrag_sdk.GraphSchema` con import
perezoso (mismo patrón que embedder_adapter B1), de modo que el backend importe
la librería sin el SDK instalado (el SDK vive en el worker B2).

`to_dict()`/`from_dict()` serializan el schema para persistirlo en el registry
vivo (tabla `tenant_schemas`, JSONB — migración 009).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class EntidadSchema:
    """Una etiqueta de entidad que el schema espera extraer."""

    label: str
    descripcion: str
    # Nombres de propiedades a extraer (todas tratadas como STRING por el SDK).
    propiedades: list[str] = field(default_factory=list)


@dataclass
class RelacionSchema:
    """Una relación dirigida entre dos labels de entidad."""

    label: str
    origen: str
    destino: str
    descripcion: str = ""


@dataclass
class DocumentSchema:
    """Schema de extracción para un tipo de documento."""

    tipo_documento: str
    descripcion: str
    entidades: list[EntidadSchema]
    relaciones: list[RelacionSchema]
    prompt_extraccion: str
    # Tipo(s) de intención del catálogo de 11 que consumen este tipo (B9/B5).
    tipos_intencion_visualizacion: list[int] = field(default_factory=list)
    # Palabras clave para la clasificación heurística del selector.
    palabras_clave: list[str] = field(default_factory=list)
    es_generado_dinamicamente: bool = False

    # ── Validación de coherencia interna ─────────────────────────────────────
    def labels_entidades(self) -> set[str]:
        return {e.label for e in self.entidades}

    def validar(self) -> None:
        """Toda relación debe referenciar entidades declaradas (regla del SDK)."""
        labels = self.labels_entidades()
        for r in self.relaciones:
            faltantes = {r.origen, r.destino} - labels
            if faltantes:
                raise ValueError(
                    f"Schema '{self.tipo_documento}': la relación '{r.label}' "
                    f"referencia entidades no declaradas: {faltantes}"
                )

    # ── Conversión a GraphRAG-SDK (import perezoso) ──────────────────────────
    def to_sdk_schema(self):
        """
        Construye un `graphrag_sdk.GraphSchema`. Import perezoso: el SDK solo
        existe en el worker de ingesta (B2), no en el backend.
        """
        self.validar()
        from graphrag_sdk import EntityType, GraphSchema, RelationType
        from graphrag_sdk.core.models import PropertyType

        entities = [
            EntityType(
                label=e.label,
                description=e.descripcion,
                properties=[PropertyType(name=p, type="STRING") for p in e.propiedades],
            )
            for e in self.entidades
        ]
        relations = [
            RelationType(
                label=r.label,
                description=r.descripcion,
                patterns=[(r.origen, r.destino)],
            )
            for r in self.relaciones
        ]
        return GraphSchema(entities=entities, relations=relations)

    # ── Serialización para el registry (JSONB) ───────────────────────────────
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> DocumentSchema:
        return cls(
            tipo_documento=data["tipo_documento"],
            descripcion=data.get("descripcion", ""),
            entidades=[EntidadSchema(**e) for e in data.get("entidades", [])],
            relaciones=[RelacionSchema(**r) for r in data.get("relaciones", [])],
            prompt_extraccion=data.get("prompt_extraccion", ""),
            tipos_intencion_visualizacion=data.get("tipos_intencion_visualizacion", []),
            palabras_clave=data.get("palabras_clave", []),
            es_generado_dinamicamente=data.get("es_generado_dinamicamente", False),
        )
