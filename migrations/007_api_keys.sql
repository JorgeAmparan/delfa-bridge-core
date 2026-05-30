-- ============================================================
-- Migración 007: Tabla api_keys
-- Fecha: 2026-05-28
-- Descripción: API Keys por organización (auth X-API-Key + alta vía Stripe).
--              Usada por app/api/auth.py (validación) y
--              app/api/routers/billing.py (alta/baja por suscripción).
--              Multi-tenant strict (RLS por org_id). La validación de auth usa
--              SUPABASE_SERVICE_KEY (bypassa RLS), igual que refresh_tokens en 001.
-- ============================================================

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,
    api_key TEXT NOT NULL,
    email TEXT,
    org_name TEXT,
    plan TEXT NOT NULL DEFAULT 'starter',
    stripe_customer_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_api_keys_api_key ON api_keys(api_key);
CREATE INDEX idx_api_keys_org_id ON api_keys(org_id);
CREATE INDEX idx_api_keys_stripe_customer ON api_keys(stripe_customer_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);

ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "api_keys_org_isolation" ON api_keys
    USING (org_id = current_setting('app.org_id', true))
    WITH CHECK (org_id = current_setting('app.org_id', true));

CREATE OR REPLACE FUNCTION update_api_keys_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_api_keys_updated_at();
