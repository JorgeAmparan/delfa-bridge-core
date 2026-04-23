import os
import json
from dotenv import load_dotenv
from google import genai
from app.core.edb import EntityDataBrain
from app.core.matrix import TraceabilityMatrix

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
RI_MODEL = "gemini-2.5-flash"


class ResponseIntelligence:
    """
    RI — Response Intelligence | Panohayan™
    Pilar de salida del pipeline. Recibe una consulta del usuario,
    obtiene contexto relevante del EDB, evalúa suficiencia de datos,
    y genera una respuesta profesional sintetizada con citación de fuentes.

    Pipeline: Query → EDB (Intent-B + vector search) → RI (análisis + síntesis) → Respuesta
    """

    def __init__(self, org_id: str = None):
        self.org_id = org_id or os.getenv("ORG_ID", "default")
        self.edb = EntityDataBrain(org_id=self.org_id)
        self.tm = TraceabilityMatrix(org_id=self.org_id)

    def responder(self, query: str, limit: int = 10) -> dict:
        """
        Pipeline completo de respuesta:
        1. Recuperar entidades relevantes del EDB (que ya aplica Intent-B)
        2. Evaluar suficiencia del contexto
        3. Sintetizar respuesta profesional con el LLM
        4. Registrar en TM
        """
        print(f"  [RI] Procesando consulta: '{query}'")

        # ── 1. Recuperación ──────────────────────────────────────────────
        entidades = self.edb.search_semantic(query, limit=limit)

        if not entidades:
            self.tm.log(
                component="RI",
                action="response_generated",
                detail={
                    "query": query,
                    "contexto_entidades": 0,
                    "suficiencia": "sin_datos",
                    "modelo": RI_MODEL,
                },
            )
            return {
                "query": query,
                "respuesta": "No encontré información relevante en los documentos procesados para responder esa consulta.",
                "fuentes": [],
                "total_fuentes": 0,
                "suficiencia": "sin_datos",
            }

        # ── 2. Evaluación de suficiencia ─────────────────────────────────
        max_sim = max(e["similarity"] for e in entidades)
        avg_sim = sum(e["similarity"] for e in entidades) / len(entidades)
        clases_presentes = list({e["entity_class"] for e in entidades})

        if max_sim >= 0.5:
            suficiencia = "alta"
        elif max_sim >= 0.35:
            suficiencia = "media"
        else:
            suficiencia = "baja"

        # ── 3. Síntesis ─────────────────────────────────────────────────
        contexto = self._construir_contexto(entidades)
        instruccion_suficiencia = self._instruccion_por_suficiencia(suficiencia)

        prompt = f"""Eres el asistente inteligente de Delfa Bridge, un middleware de IA empresarial con arquitectura Panohayan™.
Tu función es responder consultas sobre documentos que han sido procesados, normalizados y almacenados.

Pregunta del usuario: "{query}"

Entidades encontradas en los documentos (ordenadas por relevancia semántica):
{contexto}

Clases de entidad presentes: {', '.join(clases_presentes)}
Nivel de confianza del contexto: {suficiencia} (similitud máxima: {max_sim:.0%}, promedio: {avg_sim:.0%})

{instruccion_suficiencia}

Reglas:
- Responde en español, de forma directa y profesional.
- Basa tu respuesta ÚNICAMENTE en las entidades proporcionadas.
- Cita datos concretos: nombres, montos, fechas, cláusulas cuando estén disponibles.
- Si la información es insuficiente, dilo con transparencia y sugiere qué documentos podrían ayudar.
- Sé conciso pero completo (2-5 oraciones).
- NO inventes información que no esté en las entidades."""

        try:
            respuesta_llm = client.models.generate_content(
                model=RI_MODEL,
                contents=prompt,
            )
            texto = respuesta_llm.text.strip()
        except Exception as e:
            print(f"  [RI] Error en LLM: {e}")
            texto = self._respuesta_fallback(entidades, suficiencia)

        # ── 4. Fuentes (documentos únicos) ──────────────────────────────
        doc_ids = list({e["document_id"] for e in entidades if e.get("document_id")})
        doc_map = {}
        if doc_ids:
            docs = self.edb.supabase.table("documents").select(
                "id, name"
            ).in_("id", doc_ids).execute()
            doc_map = {d["id"]: d["name"] for d in docs.data}

        fuentes = []
        seen = set()
        for e in entidades:
            doc_id = e.get("document_id")
            name = doc_map.get(doc_id)
            if name and name not in seen:
                seen.add(name)
                fuentes.append({"document": name, "similarity": e["similarity"]})

        # ── 5. Trazabilidad ──────────────────────────────────────────────
        self.tm.log(
            component="RI",
            action="response_generated",
            detail={
                "query": query,
                "contexto_entidades": len(entidades),
                "suficiencia": suficiencia,
                "similitud_max": round(max_sim, 4),
                "similitud_avg": round(avg_sim, 4),
                "clases": clases_presentes,
                "modelo": RI_MODEL,
            },
        )

        return {
            "query": query,
            "respuesta": texto,
            "fuentes": fuentes,
            "total_fuentes": len(entidades),
            "suficiencia": suficiencia,
        }

    # ── Helpers internos ─────────────────────────────────────────────────

    def _construir_contexto(self, entidades: list) -> str:
        lineas = []
        for e in entidades:
            linea = f"- [{e['entity_class']}]"
            if e.get("entity_type"):
                linea += f" ({e['entity_type']})"
            linea += f" {e['entity_value']}"
            if e.get("data_text"):
                linea += f"\n  Contexto: {e['data_text']}"
            kt = e.get("knowledge_triple")
            if kt and isinstance(kt, dict) and kt.get("subject"):
                linea += f"\n  Relación: {kt['subject']} → {kt['predicate']} → {kt['object']}"
            linea += f"\n  Relevancia: {e['similarity']:.0%}"
            lineas.append(linea)
        return "\n".join(lineas)

    def _instruccion_por_suficiencia(self, suficiencia: str) -> str:
        if suficiencia == "alta":
            return "El contexto es suficiente para una respuesta completa. Responde con confianza citando datos específicos."
        if suficiencia == "media":
            return "El contexto tiene relevancia parcial. Responde con lo disponible pero indica si falta información para una respuesta completa."
        return "El contexto tiene baja relevancia. Responde con cautela, indica claramente las limitaciones, y sugiere qué tipo de documento o consulta podría dar mejores resultados."

    def _respuesta_fallback(self, entidades: list, suficiencia: str) -> str:
        valores = [e["entity_value"] for e in entidades[:3]]
        return (
            f"Encontré {len(entidades)} entidades relacionadas"
            f" (confianza: {suficiencia}): {', '.join(valores)}."
            " No pude generar una síntesis completa en este momento."
        )
