-- ============================================================
-- Migración 003: Tabla entities + búsqueda vectorial
-- Fecha: 2026-05-28
-- Descripción: Entidades extraídas por documento. Embeddings BGE-M3 (1024 dims)
--              vía pgvector. Multi-tenant strict por org_id (RLS).
--              Usada por app/core/edb.py y app/core/grg.py.
--              Incluye la función RPC match_entities() que invoca edb.py:108.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    entity_class TEXT NOT NULL,
    entity_type TEXT,
    entity_value TEXT NOT NULL,
    data_text TEXT,
    knowledge_triple JSONB,
    embedding vector(1024),                     -- BGE-M3 self-hosted (decisión #1)
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'quarantined', 'redacted')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entities_org_id ON entities(org_id);
CREATE INDEX idx_entities_document_id ON entities(document_id);
CREATE INDEX idx_entities_class ON entities(org_id, entity_class);
CREATE INDEX idx_entities_status ON entities(status);
-- Índice vectorial IVFFlat (coseno). lists ajustable según volumen.
CREATE INDEX idx_entities_embedding ON entities
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

ALTER TABLE entities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "entities_org_isolation" ON entities
    USING (org_id = current_setting('app.org_id', true))
    WITH CHECK (org_id = current_setting('app.org_id', true));

CREATE OR REPLACE FUNCTION update_entities_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_entities_updated_at();

-- ============================================================
-- RPC: match_entities — búsqueda vectorial por similitud coseno
-- Firma EXACTA esperada por app/core/edb.py:108
--   match_entities(query_embedding, match_threshold, match_count, p_org_id)
-- ============================================================
CREATE OR REPLACE FUNCTION match_entities(
    query_embedding vector(1024),
    match_threshold float,
    match_count int,
    p_org_id text
)
RETURNS TABLE (
    id uuid,
    entity_class text,
    entity_value text,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        e.id,
        e.entity_class,
        e.entity_value,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM entities e
    WHERE e.org_id = p_org_id
      AND e.status = 'active'
      AND e.embedding IS NOT NULL
      AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
$$;
