"""Read-only LangChain SQLite tools plus Tavily web-search tool."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from langchain_core.tools import tool

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ALLOWED_TABLES = {"institutions", "hospitals", "restaurants"}


def execute_db_query(table: str, sql_query: str, data_dir: Path | None = None) -> str:
    """Allow read-only, single SELECT queries against exactly one approved table."""
    if table not in ALLOWED_TABLES:
        return "Error: Invalid database selection."
    query = sql_query.strip()
    # Block PRAGMA, CTE, EXPLAIN, comments, and multi-statement inputs.
    if not re.match(r"(?is)^SELECT\s", query) or ";" in query or "--" in query or "/*" in query:
        return "Error: Only one simple SELECT query is supported."
    path = (data_dir or DATA_DIR) / f"{table}.db"
    if not path.is_file():
        return f"Error: Missing {path.name}. Build databases first."
    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=5) as connection:
            connection.execute("PRAGMA query_only = ON")
            connection.row_factory = sqlite3.Row

            def authorize(action, arg1, arg2, db, source):
                if action == sqlite3.SQLITE_SELECT:
                    return sqlite3.SQLITE_OK
                if action == sqlite3.SQLITE_READ:
                    return sqlite3.SQLITE_OK if arg1 == table else sqlite3.SQLITE_DENY
                if action == sqlite3.SQLITE_FUNCTION:
                    return sqlite3.SQLITE_DENY if str(arg2).lower() == "load_extension" else sqlite3.SQLITE_OK
                return sqlite3.SQLITE_DENY

            connection.set_authorizer(authorize)
            # Interrupt expensive queries rather than allowing infinite work.
            counter = [0]
            def bounded_progress():
                counter[0] += 1
                return 1 if counter[0] > 100 else 0
            connection.set_progress_handler(bounded_progress, 10000)
            cursor = connection.execute(query)
            rows = cursor.fetchmany(11)
            result = [dict(r) for r in rows[:10]]
            return json.dumps({"table": table, "results": result, "showing": len(result), "more_may_exist": len(rows)>10}, ensure_ascii=False, default=str)
    except sqlite3.Error as exc:
        return f"Database query error: {exc}"


@tool("InstitutionsDBTool")
def institutions_db_tool(sql_query: str) -> str:
    """Query Bangladesh institutions using one SELECT on 'institutions'. Use for institution names, counts, EIIN, districts, management and MPO status. Check the schema before assuming a column exists; never invent data."""
    return execute_db_query("institutions", sql_query)


@tool("HospitalsDBTool")
def hospitals_db_tool(sql_query: str) -> str:
    """Query Bangladesh healthcare facilities using one SELECT on 'hospitals'. Use for names, counts, agency, facility type and district. Dataset may include non-hospitals; beds, doctor counts and treatments are not provided."""
    return execute_db_query("hospitals", sql_query)


@tool("RestaurantsDBTool")
def restaurants_db_tool(sql_query: str) -> str:
    """Query Bangladesh restaurant dataset using one SELECT on 'restaurants'. Use for names, address, rating, reviews, coordinates and counts. Cuisine is not verified in this dataset."""
    return execute_db_query("restaurants", sql_query)


@tool("WebSearchTool")
def web_search_tool(query: str) -> str:
    """Search the public web for Bangladesh definitions, policy, DGHS responsibilities, current facts and general knowledge; return results with source URLs."""
    import os
    from tavily import TavilyClient
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return "Web search unavailable: configure TAVILY_API_KEY in Colab Secrets."
    try:
        response = TavilyClient(api_key=key).search(query=query, search_depth="basic", max_results=5)
        return json.dumps([{"title": r.get("title"), "url": r.get("url"), "content": (r.get("content") or "")[:1000]} for r in response.get("results", [])], ensure_ascii=False)
    except Exception as exc:
        return f"Web search error: {type(exc).__name__}: {exc}"


ALL_TOOLS = [institutions_db_tool, hospitals_db_tool, restaurants_db_tool, web_search_tool]
