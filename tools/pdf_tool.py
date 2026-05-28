"""
ARIA — Herramientas de PDF
Leer PDFs, extraer texto, generar PDFs nuevos.
"""
from pathlib import Path
from datetime import datetime

from langchain_core.tools import tool

from core.config import Config
from core.logger import get_logger

logger = get_logger("tools.pdf")
_config = Config()


@tool
def read_pdf(path: str, max_pages: int = 10) -> str:
    """Lee y extrae el texto de un archivo PDF.

    Args:
        path: Ruta absoluta del archivo PDF.
        max_pages: Máximo de páginas a leer (default 10).
    """
    if not _config.is_path_allowed(path):
        return f"⛔ Acceso denegado: '{path}'"

    p = Path(path)
    if not p.exists():
        return f"❌ Archivo no encontrado: {path}"
    if p.suffix.lower() != ".pdf":
        return f"❌ No es un archivo PDF: {path}"

    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(p))
        total_pages = len(doc)
        pages_to_read = min(total_pages, max_pages)

        text_parts = []
        for i in range(pages_to_read):
            page = doc[i]
            text = page.get_text().strip()
            if text:
                text_parts.append(f"--- Página {i+1} ---\n{text}")

        doc.close()

        if not text_parts:
            return f"📄 PDF '{p.name}' ({total_pages} páginas) — Sin texto extraíble (podría ser escaneado)."

        content = "\n\n".join(text_parts)
        # Truncate if too long
        if len(content) > 5000:
            content = content[:5000] + "\n\n... (contenido truncado)"

        suffix = f"\n\n_(Mostrando {pages_to_read} de {total_pages} páginas)_" if total_pages > pages_to_read else ""
        return f"📄 **{p.name}** ({total_pages} páginas):\n\n{content}{suffix}"

    except ImportError:
        return "❌ Módulo PyMuPDF no instalado. Ejecuta: pip install PyMuPDF"
    except Exception as e:
        logger.error(f"PDF read error: {e}")
        return f"❌ Error leyendo PDF: {e}"


@tool
def create_pdf(title: str, content: str, output_path: str = "") -> str:
    """Genera un nuevo archivo PDF con el contenido dado.

    Args:
        title: Título del documento PDF.
        content: Texto del documento (puede contener líneas múltiples).
        output_path: Ruta donde guardar el PDF. Si vacío, se guarda en C:\\ARIA\\data\\pdfs\\
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT

        # Determine output path
        if not output_path:
            pdf_dir = _config.PROJECT_ROOT / "data" / "pdfs"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
            safe_name = safe_name.strip().replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(pdf_dir / f"{timestamp}_{safe_name}.pdf")

        if not _config.is_path_allowed(output_path):
            return f"⛔ Acceso denegado: '{output_path}'"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()

        # Custom style for body
        body_style = ParagraphStyle(
            "ARIABody",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            spaceAfter=8,
            alignment=TA_LEFT,
        )

        elements = []

        # Title
        elements.append(Paragraph(title, styles["Title"]))
        elements.append(Spacer(1, 0.3 * inch))

        # Date
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        elements.append(Paragraph(f"Generado por ARIA — {date_str}", styles["Italic"]))
        elements.append(Spacer(1, 0.3 * inch))

        # Content paragraphs
        for paragraph in content.split("\n"):
            if paragraph.strip():
                # Escape HTML characters
                safe_text = (
                    paragraph
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                elements.append(Paragraph(safe_text, body_style))
            else:
                elements.append(Spacer(1, 0.15 * inch))

        doc.build(elements)
        logger.info(f"PDF created: {output_path}")
        return f"✅ PDF generado: **{title}**\n📁 Guardado en: {output_path}"

    except ImportError:
        return "❌ Módulo reportlab no instalado. Ejecuta: pip install reportlab"
    except Exception as e:
        logger.error(f"PDF creation error: {e}")
        return f"❌ Error generando PDF: {e}"


@tool
def list_pdfs(directory: str = "") -> str:
    """Lista todos los archivos PDF en un directorio.

    Args:
        directory: Directorio donde buscar PDFs. Si vacío, busca en C:\\ARIA\\data\\pdfs\\
    """
    if not directory:
        directory = str(_config.PROJECT_ROOT / "data" / "pdfs")

    if not _config.is_path_allowed(directory):
        return f"⛔ Acceso denegado: '{directory}'"

    p = Path(directory)
    if not p.exists():
        return f"📄 No se encontraron PDFs (directorio no existe: {directory})"

    pdfs = sorted(p.rglob("*.pdf"))
    if not pdfs:
        return f"📄 No se encontraron PDFs en {directory}"

    output = f"📄 **PDFs en {directory}:**\n\n"
    for pdf in pdfs[:30]:
        size_mb = pdf.stat().st_size / (1024 * 1024)
        modified = datetime.fromtimestamp(pdf.stat().st_mtime).strftime("%d/%m/%Y")
        rel = pdf.relative_to(p) if pdf.is_relative_to(p) else pdf.name
        output += f"• {rel} ({size_mb:.1f} MB) — {modified}\n"

    return output


def get_pdf_tools() -> list:
    """Return all PDF tools."""
    return [read_pdf, create_pdf, list_pdfs]
