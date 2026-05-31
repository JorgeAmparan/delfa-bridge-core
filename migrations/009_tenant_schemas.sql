-- ============================================================
-- Migración 009: Tabla tenant_schemas
-- Fecha: 2026-05-31
-- Bloque: B2 §6.4 — Registry vivo de schemas documentales por tenant.
-- Descripción: Registro de schemas de extracción activos por tenant: los del
--              catálogo del mercado alfa (manual_tecnico, msds, calibracion,
--              especificacion, ficha_tecnica) Y los derivados en runtime por el
--              generador dinámico Gemini (app/schemas_documentales/generador.py)
--              cuando un documento no calza con el catálogo. Los schemas
--              generados que demuestran utilidad (uso_contador) se proponen como
--              candidatos a integrar al catálogo permanente. Multi-tenant strict
--              (RLS por tenant_id). Acceso del backend con SUPABASE_SERVICE_KEY.
-- ============================================================

CREATE TABLE tenant_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    -- Identificador del tipo de documento: clave del catálogo
    -- ('manual_tecnico', ...) o un slug derivado por el generador.
    tipo_documento TEXT NOT NULL,
    -- Definición completa del schema (entidades, relaciones, prompt, mapeo de
    -- visualización) serializada. JSONB para consulta/filtrado.
    schema_def JSONB NOT NULL,
    -- TRUE si lo produjo el generador dinámico; FALSE si proviene del catálogo.
    es_generado_dinamicamente BOOLEAN NOT NULL DEFAULT FALSE,
    -- Veces que el schema se usó en una ingesta exitosa (señal de utilidad para
    -- promover un schema generado al catálogo permanente).
    uso_contador INTEGER NOT NULL DEFAULT 0,
    -- TRUE si fue propuesto/aceptado como candidato a catálogo permanente.
    candidato_catalogo BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_creacion TIMESTAMPTZ DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_tenant_schemas_tenant_tipo
    ON tenant_schemas(tenant_id, tipo_documento);
CREATE INDEX idx_tenant_schemas_tenant ON tenant_schemas(tenant_id);
CREATE INDEX idx_tenant_schemas_generado ON tenant_schemas(es_generado_dinamicamente);

ALTER TABLE tenant_schemas ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_schemas_isolation" ON tenant_schemas
    USING (tenant_id = current_setting('app.org_id', true))
    WITH CHECK (tenant_id = current_setting('app.org_id', true));

CREATE OR REPLACE FUNCTION update_tenant_schemas_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_tenant_schemas_updated_at
    BEFORE UPDATE ON tenant_schemas
    FOR EACH ROW EXECUTE FUNCTION update_tenant_schemas_updated_at();
