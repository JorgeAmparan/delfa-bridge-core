import os
from app.connectors.api_base import APIConnector

# ─── NOTION CONNECTOR | Panohayan™ ──────────────────────────────────────────
#
# Extrae páginas y bases de datos de Notion via API.
# Usa Integration Token (Internal Integration).
# ─────────────────────────────────────────────────────────────────────────────


class NotionConnector(APIConnector):

    CONNECTOR_NAME = "notion"
    BASE_URL = "https://api.notion.com/v1"

    def __init__(self, token: str = None, database_ids: list = None,
                 page_ids: list = None):
        super().__init__()
        self.token = token or os.getenv("NOTION_TOKEN", "")
        self.database_ids = database_ids or []
        self.page_ids = page_ids or []

    def autenticar(self) -> bool:
        if not self.token:
            print("  [Notion] Error: NOTION_TOKEN no configurado")
            return False

        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        })

        try:
            response = self.session.get(
                f"{self.BASE_URL}/users/me", timeout=10
            )
            response.raise_for_status()
            user = response.json()
            print(f"  [Notion] Autenticado: {user.get('name', 'Integration')}")
            return True
        except Exception as e:
            print(f"  [Notion] Error de autenticación: {e}")
            return False

    def _extraer_texto_bloque(self, bloque: dict) -> str:
        """Extrae texto plano de un bloque de Notion."""
        tipo = bloque.get("type", "")
        contenido = bloque.get(tipo, {})

        # Rich text blocks
        if "rich_text" in contenido:
            return "".join(
                t.get("plain_text", "")
                for t in contenido["rich_text"]
            )

        # Title
        if "title" in contenido:
            return "".join(
                t.get("plain_text", "")
                for t in contenido["title"]
            )

        return ""

    def _extraer_pagina(self, page_id: str) -> str:
        """Extrae contenido completo de una página."""
        lineas = []

        # Propiedades de la página
        try:
            pagina = self._get(f"{self.BASE_URL}/pages/{page_id}")
            props = pagina.get("properties", {})
            for nombre, prop in props.items():
                tipo = prop.get("type", "")
                if tipo == "title":
                    titulo = "".join(
                        t.get("plain_text", "")
                        for t in prop.get("title", [])
                    )
                    if titulo:
                        lineas.append(f"Título: {titulo}")
                elif tipo == "rich_text":
                    texto = "".join(
                        t.get("plain_text", "")
                        for t in prop.get("rich_text", [])
                    )
                    if texto:
                        lineas.append(f"{nombre}: {texto}")
                elif tipo in ("number", "select", "date", "email",
                              "phone_number", "url"):
                    valor = prop.get(tipo)
                    if valor is not None:
                        if isinstance(valor, dict):
                            valor = valor.get("name") or valor.get("start", "")
                        if str(valor).strip():
                            lineas.append(f"{nombre}: {valor}")
        except Exception as e:
            print(f"  [Notion] Error extrayendo propiedades: {e}")

        # Bloques hijos (contenido)
        try:
            bloques = self._get(
                f"{self.BASE_URL}/blocks/{page_id}/children",
                params={"page_size": 100}
            )
            for bloque in bloques.get("results", []):
                texto = self._extraer_texto_bloque(bloque)
                if texto:
                    lineas.append(texto)
        except Exception as e:
            print(f"  [Notion] Error extrayendo bloques: {e}")

        return "\n".join(lineas)

    def _extraer_database(self, database_id: str) -> list:
        """Extrae todos los registros de una base de datos Notion."""
        registros = []

        try:
            has_more = True
            start_cursor = None

            while has_more:
                body = {"page_size": 100}
                if start_cursor:
                    body["start_cursor"] = start_cursor

                resultado = self._post(
                    f"{self.BASE_URL}/databases/{database_id}/query",
                    json=body
                )

                for pagina in resultado.get("results", []):
                    registro = {}
                    for nombre, prop in pagina.get("properties", {}).items():
                        tipo = prop.get("type", "")
                        if tipo == "title":
                            registro[nombre] = "".join(
                                t.get("plain_text", "")
                                for t in prop.get("title", [])
                            )
                        elif tipo == "rich_text":
                            registro[nombre] = "".join(
                                t.get("plain_text", "")
                                for t in prop.get("rich_text", [])
                            )
                        elif tipo == "number":
                            registro[nombre] = prop.get("number")
                        elif tipo == "select":
                            sel = prop.get("select")
                            registro[nombre] = sel.get("name") if sel else None
                        elif tipo == "multi_select":
                            registro[nombre] = ", ".join(
                                s.get("name", "")
                                for s in prop.get("multi_select", [])
                            )
                        elif tipo == "date":
                            fecha = prop.get("date")
                            registro[nombre] = fecha.get("start") if fecha else None
                        elif tipo in ("email", "phone_number", "url"):
                            registro[nombre] = prop.get(tipo)
                        elif tipo == "checkbox":
                            registro[nombre] = prop.get("checkbox")

                    if registro:
                        registros.append(registro)

                has_more = resultado.get("has_more", False)
                start_cursor = resultado.get("next_cursor")

        except Exception as e:
            print(f"  [Notion] Error extrayendo database: {e}")

        print(f"  [Notion] {len(registros)} registros de DB {database_id[:8]}...")
        return registros

    def extraer_datos(self) -> dict:
        datos = {}

        # Bases de datos
        for db_id in self.database_ids:
            registros = self._extraer_database(db_id)
            if registros:
                datos[f"database_{db_id[:8]}"] = registros

        # Páginas individuales
        paginas_texto = []
        for page_id in self.page_ids:
            texto = self._extraer_pagina(page_id)
            if texto:
                paginas_texto.append({"page_id": page_id, "contenido": texto})

        if paginas_texto:
            datos["pages"] = paginas_texto

        return datos
