import os

from dotenv import load_dotenv

load_dotenv()

FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
FALKORDB_GRAPH = os.getenv("FALKORDB_GRAPH", "docyan")


class FalkorDBClient:
    """Skeleton client for FalkorDB graph database. Schema arrives in B1."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        graph_name: str | None = None,
    ):
        self.host = host or FALKORDB_HOST
        self.port = port or FALKORDB_PORT
        self.graph_name = graph_name or FALKORDB_GRAPH
        self._conn = None

    def connect(self):
        from falkordb import FalkorDB

        self._conn = FalkorDB(host=self.host, port=self.port)
        self._graph = self._conn.select_graph(self.graph_name)
        return self._graph

    def health(self) -> bool:
        try:
            g = self.connect()
            g.query("RETURN 1")
            return True
        except Exception:
            return False

    def query(self, cypher: str, params: dict | None = None):
        if not self._conn:
            self.connect()
        return self._graph.query(cypher, params=params)
