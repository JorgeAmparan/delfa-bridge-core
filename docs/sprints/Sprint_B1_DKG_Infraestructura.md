# Sprint Contract B1 — Infraestructura DKG: FalkorDB + BGE-M3 + Ontología base + Multi-tenancy + Versionado

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B1 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.
**Repo:** `docyan-lde-core` | **Branch de trabajo:** `sprint/B1-graph-infra`

---

## Prerequisitos

B0 + B0.5 completados y mergeados a `main`. Plataforma productiva levantada:
- Backend Fly: `docyan-lde-api` (DFW, 716 MB, health 200).
- Frontend Vercel: `docyan-lde.vercel.app` (producción HTTP 200).
- CI verde sostenido en main.
- `GEMINI_API_KEY` validada vía LiteLLM (smoke test pasó).
- 4 secrets en Fly: `JWT_SECRET`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ALLOWED_ORIGINS`.

## Contexto para Opus

Este sprint construye la **infraestructura de grafo** sobre la cual B2 montará el motor de ingesta. La decisión arquitectónica central es **topología de 4 procesos separados desde día 1, no monolítica**:

1. `docyan-lde-api` (backend principal, ya existe) — consultas, MO, clasificador, dispatcher.
2. `docyan-lde-graph` (FalkorDB self-hosted) — base de grafo persistente.
3. `docyan-lde-embedder` (BGE-M3 self-hosted) — servicio HTTP de embeddings.
4. `docyan-lde-ingest` (worker de ingesta) — se construye en B2, no aquí.

Razones de la topología: (a) imagen Docker del backend principal se mantiene en <1 GB, evitando el bloqueo de Fly que B0.5 resolvió; (b) BGE-M3 requiere PyTorch + sentence-transformers (~3 GB) que no deben contaminar el backend; (c) FalkorDB requiere volumen persistente y RPO de 15 min (decisión #12), distinto perfil que el backend stateless; (d) escalado independiente por componente según carga.

**Decisiones inviolables que rigen este sprint:**

- **BGE-M3 self-hosted es decisión firme** (decisión #1 Paso C, ratificada con argumento técnico: multilingüe superior para Pista B Magna 12-20 idiomas, soberanía de datos en industria regulada, costo cero recurrente, control de versionado para FAT). No se sustituye por OpenAI/Cohere/text-embedding-3 ni siquiera "temporalmente".
- **FalkorDB self-hosted en Fly.io es decisión firme** (decisión #7a Paso C aterrizada). No se sustituye por FalkorDB Cloud ni neo4j.
- **Multi-tenancy por `graph_name` es regla absoluta** (Adenda §2). Tenant A no puede ver datos de Tenant B bajo ninguna circunstancia.
- **Versionado in-place con `:VERSION_HISTORICA`** (decisión #11) para documentos, procedimientos, glosarios, entidades operativas; default off para términos individuales.

**Lo que este sprint NO hace** (importante para no exceder alcance):

- **No ingiere documentos.** GraphRAG-SDK se instala como dependencia y se valida que acepta BGE-M3 como embedder custom, pero la ingesta real (Docling + LlamaIndex + GraphRAG-SDK extrayendo a grafo) es scope de B2.
- **No construye schemas documentales** (catálogo, generador, registry). Eso es B2.
- **No construye cotizador con tiktoken.** Eso es B2.
- **No construye worker de ingesta como Fly app.** Eso es B2.
- **No toca DII todavía.** Se marca `@deprecated` aquí; su retiro completo es B5 cuando ya no haya callers.

## Alcance específico

### 1. Crear branch de trabajo

```bash
git checkout main
git pull origin main
git checkout -b sprint/B1-graph-infra
```

Todo el trabajo en `sprint/B1-graph-infra`. Push final + reporte; merge a main lo hace el fundador tras revisión.

### 2. Resolver pendientes técnicos diferidos de B0

Estos no son scope adicional — son tareas explícitas del sprint:

**2.1 `genai.Client()` a inicialización perezosa.**
Archivos: `app/core/ri.py`, `app/core/intent.py`. El cliente `genai.Client()` se inicializa a nivel de módulo, requiriendo `GEMINI_API_KEY` al boot. Refactorizar a factory/lazy init (función `get_genai_client()` con caché en memoria, o `functools.lru_cache(maxsize=1)`). Tests que cubran arranque sin la env var (debe arrancar el módulo; falla solo al invocar la función).

**2.2 Pin de `litellm`.**
Agregar `litellm==X.Y.Z` (versión exacta que pasó el smoke test, actualmente `1.86.2` o lo que Opus tenga instalado en el venv) tanto a `pyproject.toml` como a `requirements.docker.txt` si la imagen del backend lo va a necesitar para integrar GraphRAG-SDK. Si LiteLLM solo se usará desde el worker de ingesta (B2), agregarlo solo a `requirements.txt` (no a `requirements.docker.txt`) y documentar.

**2.3 Evaluar `cryptography==46`.**
Verificar si sigue causando conflicto con `msal` u otra dep. Si no estorba, pinear a versión actual. Si estorba, reportar PENDIENTE DE JORGE con análisis del conflicto y opciones.

### 3. Levantar FalkorDB como Fly app aparte (`docyan-lde-graph`)

**3.1 Crear `fly.graph.toml` en raíz del repo:**

Configuración para FalkorDB con volumen persistente. Recomendación inicial:

- App name: `docyan-lde-graph`.
- Región: `dfw` (mismo que backend para latencia mínima).
- Imagen: `falkordb/falkordb:latest` o pin a versión estable conocida (Opus investiga la versión actual estable y pinea).
- Puerto interno: 6379 (default FalkorDB compatible Redis).
- VM: `shared-cpu-2x` / 2 GB RAM (FalkorDB es más exigente en RAM que el backend).
- **Volumen persistente** montado en `/data` para persistencia del grafo entre reinicios.
- Sin `http_service` público — FalkorDB se accede solo desde la red privada de Fly (`*.flycast`).

**3.2 Crear app en Fly y volumen:**

```bash
flyctl apps create docyan-lde-graph
flyctl volumes create docyan_graph_data --region dfw --size 5 --app docyan-lde-graph
flyctl deploy --config fly.graph.toml --app docyan-lde-graph
```

**3.3 Configurar acceso desde backend:**

FalkorDB se accede vía DNS interno de Fly: `docyan-lde-graph.internal:6379`. Agregar como secret en backend principal:

```bash
flyctl secrets set FALKOR_HOST="docyan-lde-graph.internal" FALKOR_PORT="6379" --app docyan-lde-api
```

**3.4 Verificación:** desde el backend, hacer `PING` al FalkorDB y verificar `PONG`. Test de integración en CI con FalkorDB en docker-compose para entorno local.

### 4. Levantar BGE-M3 self-hosted como Fly app aparte (`docyan-lde-embedder`)

**4.1 Construir imagen del embedder.**

Crear directorio `embedder/` en la raíz del repo con:
- `embedder/Dockerfile` — base `python:3.11-slim`, instala `torch` (CPU), `sentence-transformers`, `fastapi`, `uvicorn`. Descarga modelo BGE-M3 en build (`BAAI/bge-m3` desde Hugging Face).
- `embedder/main.py` — FastAPI minimalista con un solo endpoint: `POST /embed` que recibe `{"texts": [...]}` y devuelve `{"embeddings": [[...], [...]], "dim": 1024}`.
- `embedder/requirements.txt` — solo lo necesario: `torch`, `sentence-transformers`, `fastapi`, `uvicorn`, `pydantic`.
- `embedder/fly.toml` — config Fly app: `docyan-lde-embedder`, región `dfw`, `shared-cpu-4x` / 4 GB RAM (BGE-M3 requiere RAM para el modelo en memoria), sin volumen persistente (modelo en imagen), sin acceso público (solo `*.flycast`).

**4.2 Reutilizar `app/embeddings/bge_client.py`.**

El cliente ya existe en el repo (lo dejó B0). Evaluar si su implementación actual hablaba HTTP a un servicio externo o cargaba el modelo en proceso. Si era in-process, **refactorizar a cliente HTTP** que apunte a `http://docyan-lde-embedder.internal:8000/embed`. Mantener la interfaz pública intacta (`get_embeddings(texts: list[str]) -> list[list[float]]`).

**4.3 Crear app y deploy:**

```bash
flyctl apps create docyan-lde-embedder
cd embedder
flyctl deploy --app docyan-lde-embedder
cd ..
```

**4.4 Configurar acceso desde backend:**

```bash
flyctl secrets set EMBEDDER_URL="http://docyan-lde-embedder.internal:8000" --app docyan-lde-api
```

**4.5 Verificación:** desde el backend, llamar a `bge_client.get_embeddings(["hola mundo"])` y verificar que devuelve vector de 1024 dim. Test de integración con embedder en docker-compose para entorno local.

### 5. Cliente FalkorDB integrado al backend principal — fachada DKG

**5.1 Refactorizar `app/graph/falkor_client.py`.**

El skeleton actual (34 LOC según contexto) se evoluciona/reemplaza por una fachada limpia:

- Crear `app/graph/dkg_client.py` (renombrado: ya no hablamos de "falkor", hablamos del DKG).
- Cliente Python de FalkorDB usando librería oficial (`falkordb` o `redis-py` con módulos FalkorDB; Opus elige y justifica).
- Interfaz orientada al dominio: `create_tenant(tenant_id)`, `create_entity(tenant_id, entity_data)`, `update_entity(...)`, `query(tenant_id, cypher, params)`, etc.
- **Multi-tenancy enforced en el cliente**: cada operación recibe `tenant_id`, internamente resuelve `graph_name` y nunca permite cross-tenant queries.
- Manejo de conexión con pool, retry con tenacity, timeout configurable.
- Logging estructurado de queries (sin valores sensibles).

**5.2 Eliminar `app/graph/falkor_client.py` antiguo si era skeleton no usado.**

### 6. Schema DKG según doc 01 — Ontología base

Implementar el schema sobre FalkorDB. **No hacer migración tradicional con SQL** — en grafo, los nodos se crean dinámicamente. Lo que sí se hace:

**6.1 Crear `app/graph/schemas/dkg_ontology.py`:**

Módulo que define en código (Pydantic models + constantes) la ontología completa del DKG según `01_Modelo_Datos_PKG.md`. Sirve para:
- Validación de payloads antes de escribir al grafo.
- Documentación viva del modelo.
- Generación de Cypher templates para creación de nodos típicos.

Nodos núcleo (con todas sus propiedades según doc 01):
- `:Tenant` — `tenant_id`, `nombre`, `tipo` (cliente_final_directo / agencia_traduccion / cliente_final_de_agencia), `idiomas_activos`, `criticidad_default`, fechas.
- `:EntidadOperativa` — `token_qr`, `tipo`, `cliente_id`, `sitio`, `estado_ciclo_vida`, `categoria_id`.
- `:CategoriaEntidad` — `nombre`, `descripcion`.
- `:DocumentoSource` — `tipo_documento`, `idioma_origen`, `version_documento`, `hash_contenido`, `fuente_ingesta` (manual / google_drive / onedrive / ftp / notion — alineado con Adenda 6.1).
- `:DocumentoTraducido` — `idioma_destino`, `origen_ingesta`, `tier_servicio`, vinculación uno-a-muchos con `:DocumentoSource`.
- `:Especificacion` — propiedades técnicas.
- `:TerminoTecnico` — términos del glosario operativo del cliente.
- `:FormaLinguistica` — BCP-47 variants.

Nodos por tipo de intención (schema base aquí; lógica completa en B7):
- `:Procedimiento`, `:Paso`, `:EPP`, `:Herramienta`, `:Advertencia` (Tipo 2).
- `:RecursoVisual`, `:Etiqueta`, `:LeyendaSimbolica` (Tipo 3).
- `:RecursoVideo`, `:Capitulo`, `:Subtitulo`, `:Transcripcion` (Tipo 4).
- `:ArbolDiagnostico`, `:NodoDecision`, `:CausaProbable`, `:AccionResolutoria` (Tipo 5).
- `:EventoOperativo`, `:CertificadoVigencia`, `:Observacion`, `:MedicionRegistrada` (Tipo 6).
- `:Alerta`, `:ReglaAlerta` (Tipo 7).
- `:Norma`, `:RequisitoNormativo` (Tipo 9 potencial).

**6.2 Provisión especial para Playbooks de Consulta (preparación Nivel A futuro).**

Aunque la implementación de Playbooks es B7+, el grafo debe estar preparado desde ahora:

- `:EventoOperativo` con `tipo = "consulta_realizada"` ya está en doc 01. Confirmar que la ontología lo soporta con propiedades suficientes: `tenant_id`, `usuario_id`, `consulta_texto`, `entidad_consultada_id`, `tipo_intencion_resuelto`, `timestamp`, `respuesta_id`, `feedback` (opcional).
- `:Observacion` también ya está en doc 01 — útil para anotaciones que en Adenda §7 son "núcleo".
- **No construir endpoints ni lógica de Playbook todavía.** Solo asegurar que el schema soporta la persistencia futura sin retrabajo.

**6.3 Aristas principales** (las que requiere el sprint para verificación; el resto se cablean cuando aparezcan en B2-B7):

- `:Tenant -[:CONTIENE]-> :EntidadOperativa`
- `:EntidadOperativa -[:CATEGORIZADA_COMO]-> :CategoriaEntidad`
- `:EntidadOperativa -[:DOCUMENTADA_POR]-> :DocumentoSource`
- `:DocumentoSource -[:TIENE_TRADUCCION]-> :DocumentoTraducido`
- `:DocumentoSource -[:VERSION_HISTORICA]-> :DocumentoSource` (versionado in-place)
- `:EntidadOperativa -[:VERSION_HISTORICA]-> :EntidadOperativa`

### 7. Multi-tenancy estricta — `graph_name` ↔ `tenant_id`

**7.1 Estrategia.**

GraphRAG-SDK ofrece multi-tenancy nativo via `graph_name`. Esto significa que **cada tenant tiene su propio grafo lógico aislado dentro de la misma instancia FalkorDB**. La regla:

```
graph_name = f"docyan_tenant_{tenant_id}"
```

**7.2 Implementación en `app/graph/dkg_client.py`:**

- Toda método público recibe `tenant_id` como primer argumento.
- Internamente resuelve `graph_name` y opera sobre ese grafo.
- **No existe método que opere sin `tenant_id` excepto operaciones administrativas explícitas** (listado de tenants, métricas globales — solo admin).
- Helpers: `with_tenant_scope(tenant_id)` decorator o context manager para asegurar enforcement.

**7.3 Verificación obligatoria (test de aislamiento):**

```python
def test_tenant_isolation():
    dkg.create_entity("tenant_A", {"token_qr": "QR-001", "tipo": "compresor"})
    dkg.create_entity("tenant_B", {"token_qr": "QR-002", "tipo": "valvula"})
    
    entities_A = dkg.query("tenant_A", "MATCH (e:EntidadOperativa) RETURN e")
    entities_B = dkg.query("tenant_B", "MATCH (e:EntidadOperativa) RETURN e")
    
    assert len(entities_A) == 1 and entities_A[0]["token_qr"] == "QR-001"
    assert len(entities_B) == 1 and entities_B[0]["token_qr"] == "QR-002"
    # Cross-tenant query debe fallar o retornar vacío, nunca filtrar
```

Este test es **bloqueador**: si falla, el sprint no cierra.

### 8. Versionado in-place

**8.1 Crear `app/graph/versioning.py`.**

- Función `version_node(tenant_id, node_id, updates)`:
  1. Lee nodo actual.
  2. Crea copia del nodo actual con etiqueta `:VersionAnterior` (o duplicación del nodo con flag `es_version_historica = true`).
  3. Conecta original ↔ histórica con arista `:VERSION_HISTORICA` con propiedad `timestamp`.
  4. Aplica `updates` al nodo original.
  5. Retorna nodo actualizado + id de versión histórica.

- Política de versionado (default on/off según decisión #11):
  - `:DocumentoSource`, `:DocumentoTraducido`, `:Procedimiento`, `:Glosario`, `:EntidadOperativa` → default on.
  - `:TerminoTecnico` individual → default off.
  - Override por configuración de tenant (futuro, no implementar UI todavía).

**8.2 Test de versionado:**

```python
def test_versioning_creates_history():
    entity = dkg.create_entity("tenant_X", {"token_qr": "QR-100", "estado": "activo"})
    dkg.version_node("tenant_X", entity["id"], {"estado": "mantenimiento"})
    
    current = dkg.get_entity("tenant_X", entity["id"])
    history = dkg.get_versions("tenant_X", entity["id"])
    
    assert current["estado"] == "mantenimiento"
    assert len(history) == 1
    assert history[0]["estado"] == "activo"
    assert "timestamp" in history[0]
```

### 9. Integración GraphRAG-SDK 1.1.1 — instalación + validación BGE-M3

**Importante:** este punto **NO ingiere documentos al grafo**. Solo instala el SDK, valida que conecta a FalkorDB, y verifica que acepta BGE-M3 como embedder custom. La ingesta real es B2.

**9.1 Agregar GraphRAG-SDK como dependencia.**

```
graphrag-sdk==1.1.1
```

A `pyproject.toml` y `requirements.txt`. Probablemente NO a `requirements.docker.txt` del backend principal (Docling + LlamaIndex y SDK pesado se quedan en el worker, B2). Confirmar y documentar.

**9.2 Resolver conflictos de versiones** ejecutando resolver real:

```bash
pip install --dry-run graphrag-sdk==1.1.1
```

Si choca con `google-genai`, `openai`, `litellm`, etc., reportar el conflicto. **No forzar pins inventados.** Si hay conflicto bloqueador, marcar PENDIENTE DE JORGE con análisis y opciones.

**9.3 Adapter de BGE-M3 para GraphRAG-SDK.**

GraphRAG-SDK acepta embedders via interfaz. Crear `app/graph/embedder_adapter.py`:

```python
class BGE_M3_Adapter:
    """Adaptador que envuelve bge_client para cumplir la interfaz del SDK."""
    def __init__(self, bge_client):
        self.bge_client = bge_client
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.bge_client.get_embeddings(texts)
    
    @property
    def dimension(self) -> int:
        return 1024
```

Si el SDK requiere otra interfaz (vía LiteLLM, vía ABC específica), construir el adapter correspondiente. **La decisión es: BGE-M3 se mantiene, el adapter se ajusta.**

**9.4 Test de integración SDK + BGE-M3:**

```python
def test_sdk_uses_bge_m3_embedder():
    from graphrag_sdk import KnowledgeGraph
    
    kg = KnowledgeGraph(
        name="docyan_tenant_test",
        host="docyan-lde-graph.internal",
        port=6379,
        embedder=BGE_M3_Adapter(bge_client)
    )
    
    # Crear un nodo simple con texto que sea embeddable
    # Verificar que el embedding generado es de dim 1024 (BGE-M3) y NO 1536 (OpenAI)
    # NO ingerir documentos reales, eso es B2
```

Este test verifica que el cableado funciona. La ingesta real espera a B2.

### 10. Marcar DII como `@deprecated`

**10.1 En `app/core/dii.py`:**

- Agregar decorator `@deprecated` (de `typing_extensions` o `deprecated` package) a la clase principal.
- Docstring de cabecera con texto explícito:

```python
"""
⚠️  DEPRECATED — DII reemplazado por GraphRAG-SDK (Adenda §2).
Este módulo se conserva temporalmente para callers existentes en
documents.py y B5 (Ingesta Bilingüe). Se elimina cuando B5 cierre.
NO usar para código nuevo. Pipeline de ingesta nuevo: ver app/graph/.
"""
```

**10.2 NO eliminar archivos ni callers.** Solo marca y advertencia. La eliminación real es post-B5.

### 11. Respaldo FalkorDB — scripts deployables

**11.1 Crear `scripts/backup_falkordb.sh`:**

- Conecta a `docyan-lde-graph.internal:6379` desde una máquina admin (puede ser ejecutado desde el backend o como cron en Fly).
- Ejecuta `BGREWRITEAOF` o `SAVE` para snapshot.
- Copia el RDB resultante a almacenamiento externo (S3-compatible, Supabase Storage, o Backblaze B2 — Opus decide según costo y simplicidad, justifica).
- Etiqueta con timestamp.
- Política: snapshot cada 15 min (RPO 15min de decisión #12), retención 7 años producción / 3 años operativo.

**11.2 Crear `scripts/restore_falkordb.sh`:**

- Descarga snapshot por fecha.
- Detiene FalkorDB en `docyan-lde-graph`.
- Reemplaza RDB.
- Reinicia FalkorDB.
- Verifica integridad con `PING` + count de nodos.

**11.3 Configurar cron en Fly:**

- Idealmente como Fly machine programada o cron job en el backend principal con scheduler (APScheduler ya en decisión #3).
- **Para este sprint:** crear los scripts y documentar cómo se invocan. Configuración del cron automático puede quedar para B6 (hardening) si requiere mucho tiempo; si Opus puede dejarlo configurado limpio en este sprint, mejor.

**11.4 Test de respaldo manual:**

- Crear datos de prueba en FalkorDB.
- Ejecutar `backup_falkordb.sh`.
- Borrar datos.
- Ejecutar `restore_falkordb.sh`.
- Verificar que los datos vuelven.

### 12. Documentación

- `docs/dkg_topology.md` — diagrama de los 4 procesos, sus puertos, sus rutas de comunicación.
- `docs/dkg_ontology.md` — referencia rápida del schema (nodos, propiedades, aristas). Generado idealmente desde `dkg_ontology.py` con introspección.
- Actualizar `README.md` con la nueva topología.
- Actualizar `CLAUDE.md` con los 3 nuevos componentes (`docyan-lde-graph`, `docyan-lde-embedder`, y referencia a `docyan-lde-ingest` que vendrá en B2).

### 13. Tests automatizados requeridos

Tests bloqueadores (si fallan, sprint no cierra):

- `tests/test_dkg_client_connection.py` — backend conecta a FalkorDB y responde PING.
- `tests/test_embedder_service.py` — backend llama a embedder y recibe vector de 1024 dim.
- `tests/test_dkg_create_tenant.py` — crear `:Tenant`, leerlo, verificar propiedades.
- `tests/test_dkg_create_entity.py` — crear `:EntidadOperativa` con propiedades del doc 01.
- `tests/test_dkg_tenant_isolation.py` — aislamiento estricto entre tenants (test §7.3).
- `tests/test_dkg_versioning.py` — versionado in-place (test §8.2).
- `tests/test_sdk_uses_bge_m3.py` — SDK usa BGE-M3 como embedder, NO OpenAI (test §9.4).
- `tests/test_graph_backup_restore.py` — backup y restore funcionan (test §11.4).
- `tests/test_genai_client_lazy.py` — módulos arrancan sin `GEMINI_API_KEY` en env (test §2.1).

Tests previos siguen pasando: 66+ del baseline B0.5.

### 14. Salida verificable (criterio último de cierre)

- ✅ `flyctl apps list` muestra `docyan-lde-api`, `docyan-lde-graph`, `docyan-lde-embedder`, los tres en estado running.
- ✅ `flyctl status --app docyan-lde-graph` muestra máquina con volumen montado.
- ✅ `flyctl status --app docyan-lde-embedder` muestra máquina respondiendo health.
- ✅ Desde el backend en producción: endpoint admin `POST /admin/tenants/test` crea un `:Tenant` de prueba, devuelve confirmación. Verificable con `curl`.
- ✅ Desde el backend en producción: endpoint admin `POST /admin/embedding/test` llama al embedder con texto "hola", devuelve vector con `dim=1024` y primeros 5 valores no nulos.
- ✅ Test de aislamiento multi-tenant pasa.
- ✅ Test de versionado pasa.
- ✅ Test de SDK + BGE-M3 pasa.
- ✅ `scripts/backup_falkordb.sh` ejecutado al menos una vez exitosamente, snapshot generado.
- ✅ CI verde en `sprint/B1-graph-infra`.
- ✅ Backend principal sigue desplegado y funcional (no se rompió por los cambios).
- ✅ Frontend Vercel sigue funcionando (no se rompió por los cambios — debería ser invariante porque B1 no toca frontend).

Si alguno de estos criterios falla, el sprint no cierra hasta que pase.

### 15. Notas para Opus sobre integración con código existente

- BGE-M3 client (`app/embeddings/bge_client.py`) ya existe; **refactorizar** a cliente HTTP que apunte al servicio externo, no recrear ni eliminar.
- Skeleton actual de `app/graph/falkor_client.py` se reemplaza por `app/graph/dkg_client.py`.
- DII (`app/core/dii.py`) **NO se elimina**, solo se marca `@deprecated`.
- Docling + LlamaIndex ya en `requirements.txt` — **no eliminar** del repo aunque no se usen en este sprint (B2 los necesita).
- Stack del backend principal (`requirements.docker.txt`) sigue siendo el de B0.5 (716 MB). NO agregar Docling/LlamaIndex/torch al backend principal — esos viven en el worker de B2.
- `app/_legacy/whatsapp_reference.py` se mantiene como en B0.5 (referencia para B9).
- `app/ingest_sources/` se mantiene como en B0.5 (stubs para B5/B12).

### 16. Reglas de ejecución

- Trabajar exclusivamente sobre la rama `sprint/B1-graph-infra`. No commitear a main directamente.
- No stubs ocultos: si algo se difiere a B2 está deliberadamente y comentado en el código.
- No diferir alcance dentro del sprint. Si algo es genuinamente bloqueador, reportar, continuar con lo demás, marcar PENDIENTE DE JORGE.
- Verdad operacional: reportar estado real de las 3 apps Fly, no proyección.
- Tests siguen pasando en cada paso, no solo al final.
- Push de la rama al cierre con todos los commits y reporte completo.
- Si conflicto de versión entre `graphrag-sdk`, `litellm`, `google-genai`, `openai` etc.: **ejecutar resolver real (`pip install --dry-run`), reportar lo que dice, no inventar pins**.

---

**Referencias:** doc 01 (Modelo Datos PKG/DKG), doc 09 (Multi-tenant y Roles), doc 10 (Stack Técnico), doc 11 (Glosario), doc 12 (Motor Traducción Rigurosa — para consumo futuro del grafo), Adenda secciones 2, 4, 5, 11, decisiones #1, #3, #11, #12 del Paso C, reporte de cierre de B0.5, smoke test pre-B1 del 30 may 2026.

---

*Fin del Sprint Contract B1.*
