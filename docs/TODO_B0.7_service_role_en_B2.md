# TODO de seguimiento B0.7 — service_role en módulos de B2 (cotizador)

> **Estado:** pendiente de aplicar AL MERGEAR B2 (`sprint/B2-ingest-engine`).
> Generado por B0.7 (`sprint/B0.7-supabase-service-role-only`, 31-may-2026).

## Contexto

B0.7 movió el backend `docyan-lde-api` a usar **exclusivamente
`SUPABASE_SERVICE_KEY`** (service_role) en los módulos del camino crítico MVP, y
eliminó la anon key (`SUPABASE_KEY`) del stack del backend. Ver
`docs/DOCYAN_Adenda_Alcance_MVP_ConsultaViva.md` y
`docs/runbook_secrets_produccion.md`.

Dos módulos del **camino crítico MVP** que también deben usar service_role viven
en la rama `sprint/B2-ingest-engine`, **no en `main`** (ni en la rama de B0.7):

| Módulo | Rol MVP |
|--------|---------|
| `app/ingesta/budget_manager.py` | Cotizador — gate financiero sin bypass; lee `tenant_budget`. |
| `app/ingesta/document_store.py` | Bucket `ingest-tmp` para el worker. |

No se pudieron tocar en B0.7 porque no existen en la rama de trabajo. El helper
ya está listo para que los adopten.

## Acción al integrar B2

En cada uno de los dos módulos, en el punto donde construyen el cliente Supabase:

```python
from app.core.supabase_client import require_supabase_config

_url, _key = require_supabase_config("budget_manager", service=True)   # o "document_store"
supabase = create_client(_url, _key)
```

- Reemplazar cualquier `os.getenv("SUPABASE_KEY")` (anon) por el helper con
  `service=True`.
- Confirmar que NINGÚN módulo de B2 backend lee ya `SUPABASE_KEY` (anon):
  `grep -rn "SUPABASE_KEY" app/ingesta/` → debe quedar en cero.
- Los tests del cotizador deben mockear el almacén (`InMemoryBudgetStore`),
  NUNCA la decisión (regla CLAUDE.md §). La validación de secrets se ejercita
  con `monkeypatch.delenv("SUPABASE_SERVICE_KEY")` esperando RuntimeError loud.

## Verificación de cierre (en el merge unificado B2+B2.1+B2.2+B0.7)

- [ ] `grep -rn '"SUPABASE_KEY"' app/` → cero (incluyendo `app/ingesta/`).
- [ ] `budget_manager` y `document_store` invocan
      `require_supabase_config(..., service=True)`.
- [ ] `scripts/smoke_test_backend.py` deja de reportar SKIP en el check del
      cotizador y pasa a PASS (porque ya existe en el árbol).
