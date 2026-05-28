"""
ARIA — Herramientas de Búsqueda Web
Buscar en internet, resumir páginas, investigar.
"""
from langchain_core.tools import tool
from core.logger import get_logger

logger = get_logger("tools.web")


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Busca información en internet usando DuckDuckGo.

    Args:
        query: Texto de búsqueda (ej: 'laptops RTX 4060 baratas').
        max_results: Número máximo de resultados (default 5).
    """
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"🔍 Sin resultados para: '{query}'"

        output = f"🌐 **Resultados para '{query}':**\n\n"
        for i, r in enumerate(results, 1):
            title = r.get("title", "Sin título")
            body = r.get("body", "")[:200]
            href = r.get("href", "")
            output += f"**{i}. {title}**\n{body}\n🔗 {href}\n\n"

        return output

    except ImportError:
        return "❌ Módulo duckduckgo-search no instalado. Ejecuta: pip install duckduckgo-search"
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return f"❌ Error buscando: {e}"


@tool
def web_news(topic: str, max_results: int = 5) -> str:
    """Busca noticias recientes sobre un tema.

    Args:
        topic: Tema a buscar (ej: 'inteligencia artificial', 'bitcoin').
        max_results: Número máximo de noticias.
    """
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.news(topic, max_results=max_results))

        if not results:
            return f"📰 Sin noticias sobre: '{topic}'"

        output = f"📰 **Noticias sobre '{topic}':**\n\n"
        for i, r in enumerate(results, 1):
            title = r.get("title", "Sin título")
            body = r.get("body", "")[:150]
            source = r.get("source", "")
            date = r.get("date", "")[:10]
            url = r.get("url", "")
            output += f"**{i}. {title}**\n📅 {date} | 📡 {source}\n{body}\n🔗 {url}\n\n"

        return output

    except ImportError:
        return "❌ Módulo duckduckgo-search no instalado."
    except Exception as e:
        logger.error(f"News search error: {e}")
        return f"❌ Error buscando noticias: {e}"


@tool
def read_webpage(url: str) -> str:
    """Lee y resume el contenido de una página web.

    Args:
        url: URL completa de la página (ej: https://example.com).
    """
    try:
        import httpx
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        resp = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts, styles, navs
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = soup.title.string if soup.title else "Sin título"
        text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive newlines
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        content = "\n".join(lines[:100])  # First 100 lines

        return (
            f"🌐 **{title}**\n"
            f"🔗 {url}\n\n"
            f"{content}\n\n"
            f"_(mostrando primeras 100 líneas)_"
        )

    except ImportError:
        return "❌ Módulos httpx/beautifulsoup4 no instalados."
    except Exception as e:
        logger.error(f"Webpage read error: {e}")
        return f"❌ Error leyendo página: {e}"


def get_web_tools() -> list:
    """Return all web search/scraping tools."""
    return [web_search, web_news, read_webpage]
