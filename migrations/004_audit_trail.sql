-- ============================================================
-- Migración 004: Tabla audit_trail (FAT — Foundation Audit Trail)
-- Fecha: 2026-05-28
-- Descripción: Registro de trazabilidad por org_id. Multi-tenant strict (RLS).
--              Usada por app/core/matrix.py (TraceabilityMatrix.log()).
--              NOTA: la cadena criptográfica SHA-256 se agrega en B6, no aquí.
--              Retención 7 años (Decisión #12) — fuera del alcance del schema.
-- ============================================================

CREATE TABLE audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,
    document_id UUID,
    entity_id UUID,
    component TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT,
    before_value JSONB DEFAULT '{}'::jsonb,
    after_value JSONB DEFAULT '{}'::jsonb,
    detail JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_trail_org_id ON audit_trail(org_id);
CREATE INDEX idx_audit_trail_document_id ON audit_trail(document_id);
CREATE INDEX idx_audit_trail_entity_id ON audit_trail(entity_id);
CREATE INDEX idx_audit_trail_component ON audit_trail(component);
CREATE INDEX idx_audit_trail_created_at ON audit_trail(created_at);

ALTER TABLE audit_trail ENABLE ROW LEVEL SECURITY;

CREATE POLICY "audit_trail_org_isolation" ON audit_trail
    USING (org_id = current_setting('app.org_id', true))
    WITH CHECK (org_id = current_setting('app.org_id', true));
