"""Offline smoke tests: run `python -m unittest discover -s tests`."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

# Minimal test stub if LangChain is not installed in the local validation runtime.
# The actual Colab run uses the genuine langchain_core package.
try:
    import langchain_core.tools
except ImportError:
    import sys
    import types
    package = types.ModuleType("langchain_core")
    package.__path__ = []
    module = types.ModuleType("langchain_core.tools")
    def tool(name):
        return lambda function: function
    module.tool = tool
    sys.modules["langchain_core"] = package
    sys.modules["langchain_core.tools"] = module

from src.tools import execute_db_query


class ToolSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        with sqlite3.connect(self.dir / "hospitals.db") as conn:
            conn.execute("CREATE TABLE hospitals (name TEXT, district TEXT)")
            conn.execute("INSERT INTO hospitals VALUES ('Example Hospital', 'Dhaka')")

    def tearDown(self):
        self.temp.cleanup()

    def test_count(self):
        result = execute_db_query("hospitals", "SELECT COUNT(*) AS total FROM hospitals", self.dir)
        self.assertIn('"total": 1', result)

    def test_delete_blocked(self):
        result = execute_db_query("hospitals", "DELETE FROM hospitals", self.dir)
        self.assertIn("Only one simple SELECT", result)

    def test_other_table_blocked(self):
        result = execute_db_query("hospitals", "SELECT name FROM restaurants", self.dir)
        self.assertIn("Database query error", result)

    def test_multiple_statements_blocked(self):
        result = execute_db_query("hospitals", "SELECT * FROM hospitals; DROP TABLE hospitals", self.dir)
        self.assertIn("Only one simple SELECT", result)


if __name__ == "__main__":
    unittest.main()
