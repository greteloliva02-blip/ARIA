"""Web search tool (cloud-safe)."""
from langchain_core.tools import tool

from core.logger import get_logger

logger = get_logger("tools.web")


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo."""
    try:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"Sin resultados para: {query}"

        lines = [f"Resultados para '{query}':"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "Sin titulo")
            body = (r.get("body") or "")[:200]
            href = r.get("href", "")
            lines.append(f"{i}. {title}\n{body}\n{href}")
        return "\n\n".join(lines)
    except Exception as e:
        logger.error("Web search error: %s", e)
        return f"No pude buscar en internet: {e}"


def get_web_tools() -> list:
    return [web_search]
