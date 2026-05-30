-- ============================================================
-- Migración 006: Tabla quarantine (cuarentena GRG)
-- Fecha: 2026-05-28
-- Descripción: Entidades en cuarentena por violación de regla. Multi-tenant
--              strict (RLS). Usada por app/core/grg.py (_mandar_cuarentena).
-- ============================================================

CREATE TABLE quarantine (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,
    entity_id UUID NOT NULL,
    rule_id UUID,
    reason TEXT NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_quarantine_org_id ON quarantine(org_id);
CREATE INDEX idx_quarantine_entity_id ON quarantine(entity_id);
CREATE INDEX idx_quarantine_resolved ON quarantine(resolved);

ALTER TABLE quarantine ENABLE ROW LEVEL SECURITY;

CREATE POLICY "quarantine_org_isolation" ON quarantine
    USING (org_id = current_setting('app.org_id', true))
    WITH CHECK (org_id = current_setting('app.org_id', true));
