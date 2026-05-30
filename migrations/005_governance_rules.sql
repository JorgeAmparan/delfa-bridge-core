-- ============================================================
-- Migración 005: Tabla governance_rules (GRG — Guardrail Governance)
-- Fecha: 2026-05-28
-- Descripción: Reglas de gobernanza por org_id. Multi-tenant strict (RLS).
--              Usada por app/core/grg.py (crear_regla / cargar reglas).
-- ============================================================

CREATE TABLE governance_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,
    entity_class TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    condition JSONB DEFAULT '{}'::jsonb,
    action TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_governance_rules_org_id ON governance_rules(org_id);
CREATE INDEX idx_governance_rules_entity_class ON governance_rules(org_id, entity_class);
CREATE INDEX idx_governance_rules_active ON governance_rules(is_active);

ALTER TABLE governance_rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "governance_rules_org_isolation" ON governance_rules
    USING (org_id = current_setting('app.org_id', true))
    WITH CHECK (org_id = current_setting('app.org_id', true));

CREATE OR REPLACE FUNCTION update_governance_rules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_governance_rules_updated_at
    BEFORE UPDATE ON governance_rules
    FOR EACH ROW EXECUTE FUNCTION update_governance_rules_updated_at();
