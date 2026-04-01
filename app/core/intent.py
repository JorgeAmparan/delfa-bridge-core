import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Configura Gemini con nuevo SDK
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
GEMINI_MODEL = "gemini-2.5-flash"

# ── Tipos de documento conocidos ─────────────────────────────────────────────

DOCUMENT_TYPES = {
    "contrato": {
        "descripcion": "Acuerdo legal entre partes",
        "entidades_clave": [
            "entidad_nombre", "monto_total", "pago_periodico",
            "fecha", "clausula", "obligacion", "penalizacion"
        ],
        "prompt_extra": (
            "Enfócate en extraer: nombres de las partes, montos pactados, "
            "fechas de vigencia, obligaciones de cada parte y penalizaciones."
        )
    },
    "factura": {
        "descripcion": "Documento de cobro por productos o servicios",
        "entidades_clave": [
            "proveedor", "cliente", "concepto", "cantidad",
            "precio_unitario", "subtotal", "iva", "total", "fecha"
        ],
        "prompt_extra": (
            "Enfócate en extraer: emisor, receptor, conceptos facturados, "
            "cantidades, precios, IVA y total a pagar."
        )
    },
    "reglamento": {
        "descripcion": "Normativa, ley o regulación",
        "entidades_clave": [
            "articulo", "obligacion", "prohibicion",
            "sancion", "autoridad", "plazo", "definicion"
        ],
        "prompt_extra": (
            "Enfócate en extraer: artículos relevantes, obligaciones, "
            "prohibiciones, sanciones y plazos establecidos."
        )
    },
    "estado_de_cuenta": {
        "descripcion": "Registro de movimientos financieros",
        "entidades_clave": [
            "cuenta", "titular", "movimiento", "cargo",
            "abono", "saldo", "fecha", "referencia"
        ],
        "prompt_extra": (
            "Enfócate en extraer: titular, número de cuenta, "
            "movimientos con fecha y monto, y saldos."
        )
    },
    "propuesta": {
        "descripcion": "Oferta comercial o técnica",
        "entidades_clave": [
            "proveedor", "cliente", "servicio", "entregable",
            "precio", "plazo", "condicion", "vigencia"
        ],
        "prompt_extra": (
            "Enfócate en extraer: empresa proponente, cliente objetivo, "
            "servicios ofrecidos, precios y condiciones."
        )
    },
    "general": {
        "descripcion": "Documento de propósito general",
        "entidades_clave": [
            "entidad_nombre", "monto_total", "fecha", "lugar"
        ],
        "prompt_extra": (
            "Extrae todas las entidades relevantes del documento."
        )
    }
}

# ── TIPO A — Intención de documento ──────────────────────────────────────────

class DocumentIntentAnalyzer:
    """
    Analiza el tipo de documento antes de que DII lo procese.
    Ajusta dinámicamente el prompt de LangExtract según el tipo detectado.
    """

    def analizar(self, texto_muestra: str) -> dict:
        """
        Detecta el tipo de documento y retorna configuración de extracción.
        Usa solo los primeros 2000 chars para ser costo-eficiente.
        """
        muestra = texto_muestra[:2000]
        tipos = list(DOCUMENT_TYPES.keys())

        prompt = f"""Analiza este fragmento de documento y determina su tipo.

Tipos posibles: {', '.join(tipos)}

Fragmento:
{muestra}

Responde ÚNICAMENTE con un JSON válido con esta estructura exacta:
{{
    "tipo": "uno de los tipos listados",
    "confianza": 0.0 a 1.0,
    "razon": "explicación breve en una línea"
}}"""

        try:
            respuesta = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            texto = respuesta.text.strip()

            # Limpiar markdown si Gemini lo agrega
            if "```" in texto:
                texto = texto.split("```")[1]
                if texto.startswith("json"):
                    texto = texto[4:]

            resultado = json.loads(texto.strip())
            tipo = resultado.get("tipo", "general")

            if tipo not in DOCUMENT_TYPES:
                tipo = "general"

            config = DOCUMENT_TYPES[tipo].copy()
            config["tipo"] = tipo
            config["confianza"] = resultado.get("confianza", 0.5)
            config["razon"] = resultado.get("razon", "")

            print(f"  [Intent-A] Tipo detectado: {tipo} "
                  f"(confianza: {config['confianza']:.0%}) — {config['razon']}")

            return config

        except Exception as e:
            print(f"  [Intent-A] Error — usando tipo general: {e}")
            config = DOCUMENT_TYPES["general"].copy()
            config["tipo"] = "general"
            config["confianza"] = 0.0
            config["razon"] = "Error en análisis"
            return config


# ── TIPO B — Intención de consulta ───────────────────────────────────────────

class QueryIntentAnalyzer:
    """
    Analiza la intención del usuario antes de buscar en EDB Lite.
    Convierte lenguaje natural en filtros de búsqueda estructurados.
    """

    def analizar(self, query: str) -> dict:
        """
        Interpreta el query y retorna:
        - query_semantico: versión optimizada para búsqueda vectorial
        - entity_classes: clases de entidad más relevantes para filtrar
        - intencion: descripción de lo que busca el usuario
        """
        prompt = f"""Analiza esta consulta de usuario sobre documentos empresariales.

Consulta: "{query}"

Clases de entidad disponibles:
- entidad_nombre (personas, empresas, organizaciones)
- monto_total (montos, precios, costos totales)
- pago_periodico (mensualidades, rentas, pagos recurrentes)
- fecha (fechas, plazos, vigencias)
- clausula (cláusulas, condiciones, términos)
- obligacion (compromisos, responsabilidades)
- penalizacion (multas, sanciones, penalidades)
- general (cualquier otra entidad)

Responde ÚNICAMENTE con un JSON válido:
{{
    "intencion": "descripción breve de lo que busca",
    "query_semantico": "versión optimizada del query para búsqueda vectorial",
    "entity_classes": ["lista", "de", "clases", "relevantes"],
    "requiere_agregacion": true o false
}}"""

        try:
            respuesta = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            texto = respuesta.text.strip()

            if "```" in texto:
                texto = texto.split("```")[1]
                if texto.startswith("json"):
                    texto = texto[4:]

            resultado = json.loads(texto.strip())

            print(f"  [Intent-B] Intención: {resultado.get('intencion', query)}")
            print(f"  [Intent-B] Clases relevantes: "
                  f"{resultado.get('entity_classes', [])}")

            return resultado

        except Exception as e:
            print(f"  [Intent-B] Error — búsqueda directa: {e}")
            return {
                "intencion": query,
                "query_semantico": query,
                "entity_classes": [],
                "requiere_agregacion": False
            }


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Intent Analyzer | Panohayan™")
    print("=" * 60)

    # Test Tipo A
    print("\n  [TEST A] Análisis de documento:")
    texto_prueba = """
    CONTRATO DE PRESTACIÓN DE SERVICIOS
    Celebrado entre SEXTO SENTIDOS representado por MARIO ARMANDO AMPARÁN ESTRADA
    y LAPPICERO STUDIO representado por JORGE LUIS AMPARÁN HERNÁNDEZ.
    El monto total del desarrollo es de $25,000.00 pesos con mensualidades de $2,000.00
    """
    dia = DocumentIntentAnalyzer()
    config = dia.analizar(texto_prueba)
    print(f"  Tipo: {config['tipo']}")
    print(f"  Entidades clave: {config['entidades_clave']}")
    print(f"  Prompt extra: {config['prompt_extra']}")

    # Test Tipo B
    print("\n  [TEST B] Análisis de queries:")
    queries = [
        "¿cuánto le debo al proveedor?",
        "¿quién firma el contrato?",
        "¿cuándo vence el contrato?",
        "¿cuál es la penalización por incumplimiento?"
    ]
    qia = QueryIntentAnalyzer()
    for q in queries:
        print(f"\n  Query: '{q}'")
        resultado = qia.analizar(q)
        print(f"  → Semántico: {resultado['query_semantico']}")
        print(f"  → Clases: {resultado['entity_classes']}")