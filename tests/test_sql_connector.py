from app.connectors.sql import SQLConnector, DRIVERS


class TestSQLConnector:
    def test_default_db_type(self):
        conn = SQLConnector()
        assert conn.db_type in DRIVERS or conn.db_type == "mysql"

    def test_password_is_string(self):
        conn = SQLConnector(password="my-password")
        assert isinstance(conn.password, str)
        assert conn.password == "my-password"

    def test_password_from_env_is_string(self):
        import os
        os.environ["SQL_PASSWORD"] = "env-password"
        conn = SQLConnector()
        assert isinstance(conn.password, str)
        del os.environ["SQL_PASSWORD"]

    def test_custom_connection_string(self):
        conn = SQLConnector(connection_string="sqlite:///test.db")
        assert conn.connection_string == "sqlite:///test.db"

    def test_drivers_map(self):
        assert "mysql" in DRIVERS
        assert "postgresql" in DRIVERS
        assert "postgres" in DRIVERS
        assert "mssql" in DRIVERS
        assert "sqlite" in DRIVERS
