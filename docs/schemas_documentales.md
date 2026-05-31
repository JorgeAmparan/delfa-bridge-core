# Librería de schemas documentales (B2 §6)

> **DOCYAN LDE™ by XCID.** Componente central (Adenda §6). El schema de extracción
> debe corresponder al **TIPO de documento + contexto del usuario**, no solo al
> dominio. Evidencia PoC: un schema de norma técnica (NOM-052) extrajo **0
> relaciones** de una ley general (LGPGIR).

## Dos capas

1. **Catálogo del mercado alfa** (`app/schemas_documentales/catalogo/`): 5 tipos
   presentes desde el diseño, ajustables por feedback de pilotos.
2. **Generador dinámico** (`generador.py`): deriva un schema con Gemini 2.5 Flash
   cuando el documento no calza con el catálogo, en vez de fallar con 0 relaciones.

La librería **no duplica** la ontología base del DKG (`app/graph/schemas/
dkg_ontology.py`). La ontología es el grafo objetivo; la librería controla *cómo
se extrae* hacia él. Coexisten.

## Los 5 tipos del catálogo

| Tipo | Entidades clave | Relaciones | Visualización |
|---|---|---|---|
| `manual_tecnico` | Procedimiento, Paso, Advertencia, Herramienta, EPP | CONTIENE_PASO, TIENE_ADVERTENCIA, REQUIERE_HERRAMIENTA, REQUIERE_EPP | Tipo 2 |
| `msds` | Sustancia, Riesgo, MedidaProteccion, EquipoProteccion, NumeroCAS | TIENE_RIESGO, REQUIERE_MEDIDA, REQUIERE_EQUIPO, IDENTIFICADA_POR | Tipo 6, 7 |
| `calibracion` | Instrumento, CertificadoCalibracion, MedicionRegistrada, FechaVencimiento, Tecnico | CERTIFICA, REGISTRA_MEDICION, VENCE_EN, EMITIDO_POR | Tipo 6, 7 |
| `especificacion` | Especificacion, ParametroTecnico, Tolerancia, UnidadMedida | DEFINE_PARAMETRO, TIENE_TOLERANCIA, EXPRESADO_EN | Tipo 1, 8 |
| `ficha_tecnica` | Producto, CaracteristicaTecnica, Modelo, Fabricante | TIENE_CARACTERISTICA, DISPONIBLE_EN_MODELO, FABRICADO_POR | Tipo 1, 3 |

Cada tipo define en código: entidades, relaciones, **prompt de extracción**
(fuerza español + ignora ruido editorial) y **mapeo a tipo(s) de intención** del
catálogo de 11 (para B9/B5).

## Representación y conversión

`DocumentSchema` (en `base.py`) es **SDK-agnóstico** y serializable
(`to_dict()`/`from_dict()` para el registry JSONB). `to_sdk_schema()` construye un
`graphrag_sdk.GraphSchema` con **import perezoso** (el SDK solo vive en el worker;
el backend importa la librería sin el SDK). Valida que toda relación referencie
entidades declaradas (lo exige el SDK).

## Selector (`selector.py`)

Estrategia: **heurística primero** (palabras clave del nombre de archivo +
primeras páginas) → si calza con el catálogo del tenant con confianza ≥0.15, se
usa; **si no calza → generador dinámico**.

**Decisión del sprint (§6.5):** la heurística alcanza ≥90% de precisión en los 5
tipos alfa (`tests/test_schema_selector.py`), así que **NO** se usa Gemini como
clasificador previo obligatorio — solo como generador de fallback, ahorrando una
llamada LLM por documento. Si en pilotos la precisión cae <90% para algún tipo,
se activa el clasificador Gemini previo (gancho previsto).

## Generador dinámico (`generador.py`)

Recibe muestra del documento + contexto (industria, operación, par lingüístico,
tier, idioma), llama a Gemini 2.5 Flash y deriva un schema operable. **Garantía
dura:** si el modelo devuelve 0 relaciones, el generador **falla explícito** (no
silencioso) — el caso LGPGIR no se repite. El LLM es inyectable para tests.

```python
from app.schemas_documentales.selector import SchemaSelector
sel = SchemaSelector(registry=mi_registry)
res = sel.seleccionar(texto_muestra, nombre_archivo, tenant_id="t1")
# res.tipo_documento, res.origen ("catalogo"|"registry"|"generado"), res.schema
```

## Registry vivo (`registry.py`, tabla `tenant_schemas` — migración 009)

Registra schemas activos por tenant (catálogo + generados). Un schema generado
que demuestra utilidad (`uso_contador ≥ 5`) se marca **candidato a catálogo
permanente**. Multi-tenant strict (RLS por `tenant_id`). Almacén abstracto:
`InMemorySchemaStore` (tests) / `SupabaseSchemaStore` (producción).
