"""
Ontología base del DKG (Document Knowledge Graph) — DOCYAN LDE™ by XCID.

B1 §6. Define EN CÓDIGO la ontología del DKG según doc 01 (Modelo Datos
PKG/DKG). Sirve para tres cosas:

  1. Validación de payloads (Pydantic v2) antes de escribir al grafo.
  2. Documentación viva del modelo (introspectable → docs/dkg_ontology.md).
  3. Catálogo de etiquetas/aristas para construir Cypher de forma consistente.

NO es una migración SQL: en grafo los nodos se crean dinámicamente. Este módulo
es la fuente de verdad de QUÉ nodos/propiedades/aristas son válidos.

Multi-tenancy (B1 §7): el aislamiento es por `graph_name = docyan_tenant_<id>`,
NO por una propiedad `tenant_id` en cada nodo. El nodo `:Tenant` vive como
metadato dentro del grafo del propio tenant.

Alcance B1: schema base + aristas mínimas de verificación. La lógica completa
por tipo de intención llega en B7; aquí solo se asegura que la ontología las
soporta sin retrabajo.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# ─────────────────────────────────────────────────────────────────────────────
# Multi-tenancy
# ─────────────────────────────────────────────────────────────────────────────

GRAPH_NAME_PREFIX = "docyan_tenant_"


def graph_name_for(tenant_id: str) -> str:
    """Resuelve el `graph_name` aislado de un tenant (regla absoluta B1 §7)."""
    tid = (tenant_id or "").strip()
    if not tid:
        raise ValueError("tenant_id no puede ser vacío.")
    return f"{GRAPH_NAME_PREFIX}{tid}"


# ─────────────────────────────────────────────────────────────────────────────
# Enums de dominio (doc 01)
# ─────────────────────────────────────────────────────────────────────────────


class TipoTenant(str, Enum):
    cliente_final_directo = "cliente_final_directo"
    agencia_traduccion = "agencia_traduccion"
    cliente_final_de_agencia = "cliente_final_de_agencia"


class FuenteIngesta(str, Enum):
    """Alineado con Adenda §6.1."""

    manual = "manual"
    google_drive = "google_drive"
    onedrive = "onedrive"
    ftp = "ftp"
    notion = "notion"


# ─────────────────────────────────────────────────────────────────────────────
# Etiquetas de nodo (labels) — catálogo canónico
# ─────────────────────────────────────────────────────────────────────────────


class NodeLabel(str, Enum):
    # Núcleo
    TENANT = "Tenant"
    ENTIDAD_OPERATIVA = "EntidadOperativa"
    CATEGORIA_ENTIDAD = "CategoriaEntidad"
    DOCUMENTO_SOURCE = "DocumentoSource"
    DOCUMENTO_TRADUCIDO = "DocumentoTraducido"
    ESPECIFICACION = "Especificacion"
    TERMINO_TECNICO = "TerminoTecnico"
    FORMA_LINGUISTICA = "FormaLinguistica"
    GLOSARIO = "Glosario"
    # Tipo 2 — Procedimientos
    PROCEDIMIENTO = "Procedimiento"
    PASO = "Paso"
    EPP = "EPP"
    HERRAMIENTA = "Herramienta"
    ADVERTENCIA = "Advertencia"
    # Tipo 3 — Recursos visuales
    RECURSO_VISUAL = "RecursoVisual"
    ETIQUETA = "Etiqueta"
    LEYENDA_SIMBOLICA = "LeyendaSimbolica"
    # Tipo 4 — Video
    RECURSO_VIDEO = "RecursoVideo"
    CAPITULO = "Capitulo"
    SUBTITULO = "Subtitulo"
    TRANSCRIPCION = "Transcripcion"
    # Tipo 5 — Diagnóstico
    ARBOL_DIAGNOSTICO = "ArbolDiagnostico"
    NODO_DECISION = "NodoDecision"
    CAUSA_PROBABLE = "CausaProbable"
    ACCION_RESOLUTORIA = "AccionResolutoria"
    # Tipo 6 — Eventos / vigencias
    EVENTO_OPERATIVO = "EventoOperativo"
    CERTIFICADO_VIGENCIA = "CertificadoVigencia"
    OBSERVACION = "Observacion"
    MEDICION_REGISTRADA = "MedicionRegistrada"
    # Tipo 7 — Alertas (SOLO administrativas — línea ABSOLUTA, ver CLAUDE.md §11.1)
    ALERTA = "Alerta"
    REGLA_ALERTA = "ReglaAlerta"
    # Tipo 9 potencial — Normativo
    NORMA = "Norma"
    REQUISITO_NORMATIVO = "RequisitoNormativo"
    # Versionado in-place (decisión #11)
    VERSION_ANTERIOR = "VersionAnterior"


# ─────────────────────────────────────────────────────────────────────────────
# Tipos de arista (relationships)
# ─────────────────────────────────────────────────────────────────────────────


class EdgeType(str, Enum):
    CONTIENE = "CONTIENE"
    CATEGORIZADA_COMO = "CATEGORIZADA_COMO"
    DOCUMENTADA_POR = "DOCUMENTADA_POR"
    TIENE_TRADUCCION = "TIENE_TRADUCCION"
    VERSION_HISTORICA = "VERSION_HISTORICA"


# ─────────────────────────────────────────────────────────────────────────────
# Modelos Pydantic de validación de propiedades por nodo (doc 01)
# ─────────────────────────────────────────────────────────────────────────────


class _BaseNode(BaseModel):
    # Permite propiedades extra (el grafo es flexible) pero valida las nombradas.
    model_config = ConfigDict(extra="allow", use_enum_values=True)


class TenantProps(_BaseNode):
    tenant_id: str
    nombre: str
    tipo: TipoTenant
    idiomas_activos: list[str] = Field(default_factory=list)
    criticidad_default: str | None = None
    fecha_alta: str | None = None
    fecha_actualizacion: str | None = None


class EntidadOperativaProps(_BaseNode):
    token_qr: str
    tipo: str | None = None
    cliente_id: str | None = None
    sitio: str | None = None
    estado_ciclo_vida: str | None = None
    categoria_id: str | None = None


class CategoriaEntidadProps(_BaseNode):
    nombre: str
    descripcion: str | None = None


class DocumentoSourceProps(_BaseNode):
    tipo_documento: str
    idioma_origen: str
    version_documento: str | None = None
    hash_contenido: str | None = None
    fuente_ingesta: FuenteIngesta = FuenteIngesta.manual


class DocumentoTraducidoProps(_BaseNode):
    idioma_destino: str
    origen_ingesta: str | None = None
    tier_servicio: str | None = None


class EspecificacionProps(_BaseNode):
    nombre: str
    valor: str | None = None
    unidad: str | None = None


class TerminoTecnicoProps(_BaseNode):
    termino: str
    definicion: str | None = None


class FormaLinguisticaProps(_BaseNode):
    # Variantes BCP-47 (es-MX, en-US, ...).
    bcp47: str
    forma: str | None = None


class EventoOperativoProps(_BaseNode):
    """
    Soporta `tipo = "consulta_realizada"` para Playbooks de Consulta (B1 §6.2,
    preparación Nivel A futuro). Las props de consulta son opcionales aquí; la
    lógica de Playbook llega en B7. NO se construye endpoint todavía.
    """

    tipo: str
    usuario_id: str | None = None
    consulta_texto: str | None = None
    entidad_consultada_id: str | None = None
    tipo_intencion_resuelto: str | None = None
    timestamp: str | None = None
    respuesta_id: str | None = None
    feedback: str | None = None


class ObservacionProps(_BaseNode):
    # Núcleo para anotaciones (Adenda §7).
    texto: str
    autor_id: str | None = None
    timestamp: str | None = None


# Mapa label → modelo de validación. Solo los nodos con contrato de props
# estricto en B1 están aquí; el resto se validan laxamente (extra="allow").
NODE_PROPERTY_MODELS: dict[str, type[_BaseNode]] = {
    NodeLabel.TENANT.value: TenantProps,
    NodeLabel.ENTIDAD_OPERATIVA.value: EntidadOperativaProps,
    NodeLabel.CATEGORIA_ENTIDAD.value: CategoriaEntidadProps,
    NodeLabel.DOCUMENTO_SOURCE.value: DocumentoSourceProps,
    NodeLabel.DOCUMENTO_TRADUCIDO.value: DocumentoTraducidoProps,
    NodeLabel.ESPECIFICACION.value: EspecificacionProps,
    NodeLabel.TERMINO_TECNICO.value: TerminoTecnicoProps,
    NodeLabel.FORMA_LINGUISTICA.value: FormaLinguisticaProps,
    NodeLabel.EVENTO_OPERATIVO.value: EventoOperativoProps,
    NodeLabel.OBSERVACION.value: ObservacionProps,
}


# ─────────────────────────────────────────────────────────────────────────────
# Política de versionado in-place (decisión #11 / B1 §8)
# ─────────────────────────────────────────────────────────────────────────────

# default ON: cambios crean versión histórica. default OFF: cambios in-place sin historia.
VERSIONING_DEFAULT_ON: frozenset[str] = frozenset(
    {
        NodeLabel.DOCUMENTO_SOURCE.value,
        NodeLabel.DOCUMENTO_TRADUCIDO.value,
        NodeLabel.PROCEDIMIENTO.value,
        NodeLabel.GLOSARIO.value,
        NodeLabel.ENTIDAD_OPERATIVA.value,
    }
)

VERSIONING_DEFAULT_OFF: frozenset[str] = frozenset(
    {
        NodeLabel.TERMINO_TECNICO.value,
    }
)


def versioning_enabled_for(label: str) -> bool:
    """Política default de versionado por etiqueta (decisión #11)."""
    if label in VERSIONING_DEFAULT_OFF:
        return False
    return label in VERSIONING_DEFAULT_ON


# Aristas principales del sprint (B1 §6.3): (origen, tipo, destino).
CORE_EDGES: tuple[tuple[str, str, str], ...] = (
    (NodeLabel.TENANT.value, EdgeType.CONTIENE.value, NodeLabel.ENTIDAD_OPERATIVA.value),
    (NodeLabel.ENTIDAD_OPERATIVA.value, EdgeType.CATEGORIZADA_COMO.value, NodeLabel.CATEGORIA_ENTIDAD.value),
    (NodeLabel.ENTIDAD_OPERATIVA.value, EdgeType.DOCUMENTADA_POR.value, NodeLabel.DOCUMENTO_SOURCE.value),
    (NodeLabel.DOCUMENTO_SOURCE.value, EdgeType.TIENE_TRADUCCION.value, NodeLabel.DOCUMENTO_TRADUCIDO.value),
    (NodeLabel.DOCUMENTO_SOURCE.value, EdgeType.VERSION_HISTORICA.value, NodeLabel.DOCUMENTO_SOURCE.value),
    (NodeLabel.ENTIDAD_OPERATIVA.value, EdgeType.VERSION_HISTORICA.value, NodeLabel.ENTIDAD_OPERATIVA.value),
)


def validate_node(label: str, props: dict) -> dict:
    """
    Valida y normaliza las propiedades de un nodo contra su modelo Pydantic.

    - Si la etiqueta no es conocida → ValueError (no se permiten labels arbitrarios).
    - Si la etiqueta tiene modelo estricto → valida y devuelve dict normalizado.
    - Si no tiene modelo estricto (pero es label válido) → devuelve props tal cual.
    """
    valid_labels = {m.value for m in NodeLabel}
    if label not in valid_labels:
        raise ValueError(
            f"Etiqueta de nodo desconocida: '{label}'. "
            f"Debe estar en la ontología DKG (ver NodeLabel)."
        )
    model = NODE_PROPERTY_MODELS.get(label)
    if model is None:
        return dict(props)
    return model(**props).model_dump(exclude_none=True)


def ontology_summary() -> dict:
    """Introspección de la ontología (para generar docs/dkg_ontology.md)."""
    return {
        "graph_name_prefix": GRAPH_NAME_PREFIX,
        "node_labels": [m.value for m in NodeLabel],
        "edge_types": [m.value for m in EdgeType],
        "core_edges": [list(e) for e in CORE_EDGES],
        "validated_nodes": {
            label: list(model.model_fields.keys())
            for label, model in NODE_PROPERTY_MODELS.items()
        },
        "versioning_default_on": sorted(VERSIONING_DEFAULT_ON),
        "versioning_default_off": sorted(VERSIONING_DEFAULT_OFF),
    }
