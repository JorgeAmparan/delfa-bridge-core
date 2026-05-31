# DKG — Ontología base (referencia rápida)

> **DOCYAN LDE™ by XCID — B1.** Fuente de verdad en código:
> [`app/graph/schemas/dkg_ontology.py`](../app/graph/schemas/dkg_ontology.py).
> Este documento se deriva de `ontology_summary()` (introspección). Si cambia el
> código, regenerar. Modelo según doc 01 (Modelo Datos PKG/DKG).

## Multi-tenancy

Aislamiento **nativo por grafo**, no por propiedad. Cada tenant tiene su propio
grafo lógico en la misma instancia FalkorDB:

```
graph_name = "docyan_tenant_" + tenant_id
```

`DKGClient` confina toda operación al grafo del tenant vía `select_graph()`.
No existe ruta pública para una query cruzada entre tenants (regla absoluta §7).

## Nodos núcleo (con propiedades validadas)

| Label | Propiedades |
|---|---|
| `:Tenant` | `tenant_id`, `nombre`, `tipo` (cliente_final_directo / agencia_traduccion / cliente_final_de_agencia), `idiomas_activos`, `criticidad_default`, `fecha_alta`, `fecha_actualizacion` |
| `:EntidadOperativa` | `token_qr` (req), `tipo`, `cliente_id`, `sitio`, `estado_ciclo_vida`, `categoria_id` |
| `:CategoriaEntidad` | `nombre`, `descripcion` |
| `:DocumentoSource` | `tipo_documento`, `idioma_origen`, `version_documento`, `hash_contenido`, `fuente_ingesta` (manual / google_drive / onedrive / ftp / notion) |
| `:DocumentoTraducido` | `idioma_destino`, `origen_ingesta`, `tier_servicio` |
| `:Especificacion` | `nombre`, `valor`, `unidad` |
| `:TerminoTecnico` | `termino`, `definicion` |
| `:FormaLinguistica` | `bcp47`, `forma` |
| `:EventoOperativo` | `tipo`, `usuario_id`, `consulta_texto`, `entidad_consultada_id`, `tipo_intencion_resuelto`, `timestamp`, `respuesta_id`, `feedback` |
| `:Observacion` | `texto`, `autor_id`, `timestamp` |

`:EventoOperativo` con `tipo="consulta_realizada"` y `:Observacion` están listos
para **Playbooks de Consulta** (Nivel A, B7+) — el schema ya los soporta; la
lógica se construye en B7 (B1 §6.2).

## Nodos por tipo de intención (schema base; lógica en B7)

- **Tipo 2 — Procedimientos:** `:Procedimiento`, `:Paso`, `:EPP`, `:Herramienta`, `:Advertencia`
- **Tipo 3 — Visuales:** `:RecursoVisual`, `:Etiqueta`, `:LeyendaSimbolica`
- **Tipo 4 — Video:** `:RecursoVideo`, `:Capitulo`, `:Subtitulo`, `:Transcripcion`
- **Tipo 5 — Diagnóstico:** `:ArbolDiagnostico`, `:NodoDecision`, `:CausaProbable`, `:AccionResolutoria`
- **Tipo 6 — Eventos/vigencias:** `:EventoOperativo`, `:CertificadoVigencia`, `:Observacion`, `:MedicionRegistrada`
- **Tipo 7 — Alertas (SOLO administrativas, línea ABSOLUTA CLAUDE.md §11.1):** `:Alerta`, `:ReglaAlerta`
- **Tipo 9 potencial — Normativo:** `:Norma`, `:RequisitoNormativo`
- **Versionado:** `:VersionAnterior`

## Aristas núcleo (B1 §6.3)

```
(:Tenant)            -[:CONTIENE]->          (:EntidadOperativa)
(:EntidadOperativa)  -[:CATEGORIZADA_COMO]-> (:CategoriaEntidad)
(:EntidadOperativa)  -[:DOCUMENTADA_POR]->   (:DocumentoSource)
(:DocumentoSource)   -[:TIENE_TRADUCCION]->  (:DocumentoTraducido)
(:DocumentoSource)   -[:VERSION_HISTORICA]-> (:DocumentoSource)
(:EntidadOperativa)  -[:VERSION_HISTORICA]-> (:EntidadOperativa)
```

El resto de aristas se cablean cuando aparezcan en B2-B7.

## Versionado in-place (decisión #11 — B1 §8)

El nodo vivo conserva su `id` estable. Cada cambio versionado deja una copia
inmutable `:VersionAnterior` (con `version_of`, `version_label`, `timestamp`)
enlazada por `:VERSION_HISTORICA {timestamp}`. La copia NO lleva la etiqueta
original → no contamina las consultas de dominio.

| Default ON | Default OFF |
|---|---|
| `:DocumentoSource`, `:DocumentoTraducido`, `:Procedimiento`, `:Glosario`, `:EntidadOperativa` | `:TerminoTecnico` (término individual) |

Implementación: [`app/graph/versioning.py`](../app/graph/versioning.py).

## Embeddings

BGE-M3 self-hosted, **1024 dim** (decisión #1 — NO 1536 de OpenAI). El adapter
[`app/graph/embedder_adapter.py`](../app/graph/embedder_adapter.py) implementa la
interfaz `Embedder` del GraphRAG-SDK envolviendo el cliente HTTP `bge_client`.
La ingesta real (GraphRAG-SDK escribiendo al grafo) es **B2**.
