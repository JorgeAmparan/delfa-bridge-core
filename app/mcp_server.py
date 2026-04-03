import os
import asyncio
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from app.core.edb import EntityDataBrain
from app.core.dii import DigestInputIntelligence
from app.core.grg import GovernanceGuardrails
from app.core.matrix import TraceabilityMatrix

load_dotenv()

# ─── PANOHAYAN™ MCP SERVER ────────────────────────────────────────────────────
#
# Expone Delfa Bridge como MCP server.
# Permite conectar Panohayan™ directamente a Claude y ecosistema MCP.
# ─────────────────────────────────────────────────────────────────────────────

server = Server("delfa-bridge")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lista las herramientas disponibles en Panohayan™."""
    return [
        Tool(
            name="search_knowledge",
            description=(
                "Busca información en el knowledge base de la organización. "
                "Acepta preguntas en lenguaje natural y retorna entidades "
                "relevantes extraídas de documentos procesados. "
                "Usa esto para responder preguntas sobre contratos, facturas, "
                "reglamentos y cualquier documento empresarial."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Pregunta o consulta en lenguaje natural"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de resultados (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_document_trail",
            description=(
                "Obtiene el audit trail completo de un documento. "
                "Muestra cada acción realizada sobre el documento "
                "con trazabilidad total hacia la fuente original."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "ID del documento en Delfa Bridge"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="list_documents",
            description=(
                "Lista todos los documentos procesados por la organización. "
                "Incluye nombre, tipo, estado y fecha de procesamiento."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "org_id": {
                        "type": "string",
                        "description": "ID de la organización (opcional)"
                    }
                }
            }
        ),
        Tool(
            name="get_knowledge_summary",
            description=(
                "Obtiene un resumen del knowledge base: "
                "total de documentos, entidades, y estado del EDB Lite."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Ejecuta una herramienta de Panohayan™."""

    org_id = os.getenv("ORG_ID", "default")

    if name == "search_knowledge":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)

        edb = EntityDataBrain(org_id=org_id)
        resultados = edb.search_semantic(query, limit=limit)

        # Log en TM
        tm = TraceabilityMatrix(org_id=org_id)
        tm.log(
            component="MCP",
            action="searched",
            detail={"query": query, "resultados": len(resultados)}
        )

        if not resultados:
            return [TextContent(
                type="text",
                text=f"No se encontraron resultados para: '{query}'"
            )]

        texto = f"Resultados para '{query}':\n\n"
        for r in resultados:
            texto += (
                f"• [{r['entity_class']}] {r['entity_value']} "
                f"(relevancia: {r['similarity']:.0%})\n"
            )

        return [TextContent(type="text", text=texto)]

    elif name == "get_document_trail":
        document_id = arguments.get("document_id", "")

        tm = TraceabilityMatrix(org_id=org_id)
        trail = tm.get_document_trail(document_id)

        if not trail:
            return [TextContent(
                type="text",
                text=f"No se encontró trail para documento: {document_id}"
            )]

        texto = f"Audit trail — {len(trail)} eventos:\n\n"
        for evento in trail:
            texto += (
                f"• [{evento['component']}] {evento['action']} "
                f"— {evento['created_at'][:19]}\n"
            )

        return [TextContent(type="text", text=texto)]

    elif name == "list_documents":
        from supabase import create_client
        supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

        resultado = supabase.table("documents").select(
            "id, name, source_type, status, processed_at"
        ).eq("org_id", org_id).order(
            "created_at", desc=True
        ).execute()

        if not resultado.data:
            return [TextContent(
                type="text",
                text="No hay documentos procesados."
            )]

        texto = f"Documentos en Delfa Bridge ({len(resultado.data)}):\n\n"
        for doc in resultado.data:
            texto += (
                f"• {doc['name']} [{doc['source_type']}] "
                f"— {doc['status']} "
                f"| ID: {doc['id']}\n"
            )

        return [TextContent(type="text", text=texto)]

    elif name == "get_knowledge_summary":
        edb = EntityDataBrain(org_id=org_id)
        summary = edb.get_summary()

        texto = (
            f"Knowledge Base Summary — Panohayan™\n\n"
            f"Organización : {summary['org_id']}\n"
            f"Documentos   : {summary['total_documentos']}\n"
            f"Entidades    : {summary['total_entidades']}\n"
        )

        return [TextContent(type="text", text=texto)]

    return [TextContent(type="text", text=f"Herramienta no reconocida: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
    