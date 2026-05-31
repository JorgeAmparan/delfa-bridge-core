-- ============================================================
-- Migración 008: Tabla tenant_budget
-- Fecha: 2026-05-31
-- Bloque: B2 §7.4 — Cotizador pre-ingesta (protección financiera multinivel).
-- Descripción: Saldo prepagado finito SIN auto-recharge + hard caps por
--              documento y por sesión de ingesta. El cotizador
--              (app/ingesta/cotizador.py) consulta esta tabla ANTES de invocar
--              a GraphRAG-SDK; sin saldo suficiente NO hay ingesta (gate sin
--              bypass — ver CLAUDE.md / Adenda §8). Justificación operativa:
--              incidente PoC 28-may-2026 ($5,000 Gemini por ingesta sin control
--              de costo). Multi-tenant strict (RLS por tenant_id). El acceso del
--              backend usa SUPABASE_SERVICE_KEY (bypassa RLS), igual que
--              refresh_tokens (001) y api_keys (007); la RLS es defensa en
--              profundidad contra conexiones con clave anónima.
-- ============================================================

CREATE TABLE tenant_budget (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    -- Saldo prepagado en USD. Finito, sin auto-recharge: el cliente recarga
    -- manualmente (ultima_recarga registra el evento). El cotizador rechaza
    -- ingestas cuyo costo estimado exceda este saldo.
    saldo_actual_usd NUMERIC(12, 4) NOT NULL DEFAULT 0,
    -- Hard cap por documento individual. Default $5 USD para el mercado alfa.
    hard_cap_por_documento NUMERIC(12, 4) NOT NULL DEFAULT 5.0000,
    -- Hard cap por sesión de ingesta (acumulado de varios documentos). Default $20.
    hard_cap_por_sesion NUMERIC(12, 4) NOT NULL DEFAULT 20.0000,
    -- Moneda de referencia (USD por defecto; MXN reportable para el PM).
    moneda TEXT NOT NULL DEFAULT 'USD',
    ultima_recarga TIMESTAMPTZ,
    fecha_creacion TIMESTAMPTZ DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_tenant_budget_tenant ON tenant_budget(tenant_id);

ALTER TABLE tenant_budget ENABLE ROW LEVEL SECURITY;

-- Aislamiento multi-tenant: la GUC app.org_id la fija la app (org_id == tenant_id
-- en DOCYAN). Consistente con la política de api_keys (007).
CREATE POLICY "tenant_budget_isolation" ON tenant_budget
    USING (tenant_id = current_setting('app.org_id', true))
    WITH CHECK (tenant_id = current_setting('app.org_id', true));

CREATE OR REPLACE FUNCTION update_tenant_budget_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_tenant_budget_updated_at
    BEFORE UPDATE ON tenant_budget
    FOR EACH ROW EXECUTE FUNCTION update_tenant_budget_updated_at();
