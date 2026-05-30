-- ============================================================
-- Migración 002: Tabla documents
-- Fecha: 2026-05-28
-- Descripción: Documentos ingeridos por tenant (org_id). Multi-tenant strict
--              vía RLS, consistente con 001. Usada por app/api/routers/documents.py
--              y app/core/edb.py / grg.py.
-- ============================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,
    name TEXT NOT NULL,
    doc_type TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'success', 'error', 'quarantined')),
    source TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_org_id ON documents(org_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_org_name ON documents(org_id, name);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "documents_org_isolation" ON documents
    USING (org_id = current_setting('app.org_id', true))
    WITH CHECK (org_id = current_setting('app.org_id', true));

-- Trigger updated_at (reutiliza patrón de 001)
CREATE OR REPLACE FUNCTION update_documents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_documents_updated_at();
