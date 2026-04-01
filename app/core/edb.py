import os
import hashlib
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI

load_dotenv()

class EntityDataBrain:
    """
    EDB Lite — Entity Data Brain
    Memoria híbrida: relacional + vectorial (pgvector)
    Persistencia y búsqueda semántica de entidades extraídas por DII.
    """

    def __init__(self):
        self.org_id = os.getenv("ORG_ID", "default")
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        # OpenAI para embeddings (text-embedding-3-small — económico y preciso)
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dims = 1536

    # ── Embeddings ───────────────────────────────────────────────────────────

    def _generar_embedding(self, texto: str) -> list:
        """Genera embedding vectorial de un texto."""
        respuesta = self.openai.embeddings.create(
            model=self.embedding_model,
            input=texto.strip()
        )
        return respuesta.data[0].embedding

    # ── Store ─────────────────────────────────────────────────────────────────

    def store_embedding(self, entity_id: str, entity_class: str,
                        entity_value: str) -> bool:
        """
        Genera embedding y lo persiste en la entidad existente.
        Llamar después de que DII guarda la entidad en Supabase.
        """
        try:
            texto_para_embedding = f"{entity_class}: {entity_value}"
            embedding = self._generar_embedding(texto_para_embedding)

            self.supabase.table("entities").update({
                "embedding": embedding
            }).eq("id", entity_id).execute()

            print(f"  [EDB] Embedding guardado: {entity_class} = {entity_value[:40]}")
            return True

        except Exception as e:
            print(f"  [EDB] Error generando embedding: {e}")
            return False

    def store_document_embeddings(self, document_id: str) -> int:
        """
        Genera embeddings para todas las entidades de un documento.
        Útil para procesar en batch después de DII.
        """
        resultado = self.supabase.table("entities").select(
            "id, entity_class, entity_value"
        ).eq("document_id", document_id).eq(
            "org_id", self.org_id
        ).is_("embedding", "null").execute()

        entidades = resultado.data
        count = 0

        for entidad in entidades:
            ok = self.store_embedding(
                entity_id=entidad["id"],
                entity_class=entidad["entity_class"],
                entity_value=entidad["entity_value"]
            )
            if ok:
                count += 1

        print(f"  [EDB] {count} embeddings generados para documento {document_id}")
        return count

    # ── Search ────────────────────────────────────────────────────────────────

    def search_semantic(self, query: str, limit: int = 5) -> list:
        """
        Búsqueda semántica por similitud coseno.
        Encuentra entidades conceptualmente relacionadas con el query.
        """
        print(f"  [EDB] Búsqueda semántica: '{query}'")

        query_embedding = self._generar_embedding(query)

        resultado = self.supabase.rpc("match_entities", {
            "query_embedding": query_embedding,
            "match_threshold": 0.5,
            "match_count": limit,
            "p_org_id": self.org_id
        }).execute()

        return resultado.data

    def search_by_class(self, entity_class: str, limit: int = 20) -> list:
        """Recupera entidades por tipo exacto."""
        resultado = self.supabase.table("entities").select(
            "id, entity_class, entity_value, normalized_value, confidence, created_at"
        ).eq("entity_class", entity_class).eq(
            "org_id", self.org_id
        ).eq("status", "active").limit(limit).execute()

        return resultado.data

    def search_by_document(self, document_id: str) -> list:
        """Todas las entidades de un documento específico."""
        resultado = self.supabase.table("entities").select(
            "id, entity_class, entity_value, normalized_value, status, created_at"
        ).eq("document_id", document_id).eq(
            "org_id", self.org_id
        ).execute()

        return resultado.data

    def get_summary(self) -> dict:
        """Resumen del EDB Lite para esta organización."""
        docs = self.supabase.table("documents").select(
            "id", count="exact"
        ).eq("org_id", self.org_id).execute()

        entities = self.supabase.table("entities").select(
            "id", count="exact"
        ).eq("org_id", self.org_id).eq("status", "active").execute()

        return {
            "org_id": self.org_id,
            "total_documentos": docs.count,
            "total_entidades": entities.count,
        }


if __name__ == "__main__":
    # Test EDB Lite
    edb = EntityDataBrain()

    print("=" * 60)
    print("  EDB Lite — Entity Data Brain | Panohayan™")
    print("=" * 60)

    # Resumen actual
    summary = edb.get_summary()
    print(f"\n  Organización: {summary['org_id']}")
    print(f"  Documentos:   {summary['total_documentos']}")
    print(f"  Entidades:    {summary['total_entidades']}")

    # Buscar por clase
    print("\n  [TEST] Entidades tipo 'entidad_nombre':")
    nombres = edb.search_by_class("entidad_nombre", limit=5)
    for n in nombres:
        print(f"    → {n['entity_value']}")

    print("\n  [TEST] Entidades tipo 'monto_total':")
    montos = edb.search_by_class("monto_total", limit=5)
    for m in montos:
        print(f"    → {m['entity_value']}")
