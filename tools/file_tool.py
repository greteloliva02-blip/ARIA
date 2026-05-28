"""
ARIA — Herramientas de Gestión de Archivos
Listar, leer, mover, renombrar, buscar, organizar archivos locales.
"""
import os
import shutil
from pathlib import Path
from datetime import datetime

from langchain_core.tools import tool

from core.config import Config
from core.logger import get_logger

logger = get_logger("tools.files")
_config = Config()


def _check_path(path: str) -> str | None:
    """Return error message if path is not allowed, else None."""
    if not _config.is_path_allowed(path):
        return f"⛔ Acceso denegado: '{path}' no está en los directorios permitidos."
    return None


@tool
def list_directory(path: str) -> str:
    """Lista archivos y carpetas en un directorio. Úsalo para explorar los archivos del usuario.

    Args:
        path: Ruta absoluta del directorio a listar (ej: C:\\Users\\grete\\Documents)
    """
    err = _check_path(path)
    if err:
        return err
    p = Path(path)
    if not p.exists():
        return f"❌ El directorio no existe: {path}"
    if not p.is_dir():
        return f"❌ No es un directorio: {path}"

    items = []
    try:
        for entry in sorted(p.iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                count = sum(1 for _ in entry.iterdir()) if entry.exists() else 0
                items.append(f"📁 {entry.name}/ ({count} elementos)")
            else:
                size = entry.stat().st_size
                if size < 1024:
                    sz = f"{size} B"
                elif size < 1024 * 1024:
                    sz = f"{size/1024:.1f} KB"
                elif size < 1024 * 1024 * 1024:
                    sz = f"{size/1024/1024:.1f} MB"
                else:
                    sz = f"{size/1024/1024/1024:.2f} GB"
                items.append(f"📄 {entry.name} ({sz})")
    except PermissionError:
        return f"⛔ Sin permisos para leer: {path}"

    if not items:
        return f"📂 Directorio vacío: {path}"
    header = f"📂 **{path}** ({len(items)} elementos):\n"
    return header + "\n".join(items[:50])  # Cap at 50


@tool
def read_text_file(path: str, max_lines: int = 100) -> str:
    """Lee el contenido de un archivo de texto.

    Args:
        path: Ruta absoluta del archivo a leer.
        max_lines: Máximo de líneas a leer (default 100).
    """
    err = _check_path(path)
    if err:
        return err
    p = Path(path)
    if not p.exists():
        return f"❌ Archivo no encontrado: {path}"
    if not p.is_file():
        return f"❌ No es un archivo: {path}"

    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        total = len(lines)
        content = "\n".join(lines[:max_lines])
        suffix = f"\n\n... ({total - max_lines} líneas más)" if total > max_lines else ""
        return f"📄 **{p.name}** ({total} líneas):\n```\n{content}{suffix}\n```"
    except Exception as e:
        return f"❌ Error leyendo archivo: {e}"


@tool
def move_file(source: str, destination: str) -> str:
    """Mueve un archivo o carpeta de una ubicación a otra.

    Args:
        source: Ruta absoluta del archivo/carpeta origen.
        destination: Ruta absoluta del destino.
    """
    for p in [source, destination]:
        err = _check_path(p)
        if err:
            return err

    src = Path(source)
    if not src.exists():
        return f"❌ No existe: {source}"

    dst = Path(destination)
    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.move(str(src), str(dst))
        logger.info(f"Moved: {source} → {destination}")
        return f"✅ Movido: {src.name} → {destination}"
    except Exception as e:
        return f"❌ Error moviendo: {e}"


@tool
def rename_file(path: str, new_name: str) -> str:
    """Renombra un archivo o carpeta.

    Args:
        path: Ruta absoluta del archivo/carpeta.
        new_name: Nuevo nombre (solo el nombre, no la ruta completa).
    """
    err = _check_path(path)
    if err:
        return err
    p = Path(path)
    if not p.exists():
        return f"❌ No existe: {path}"

    new_path = p.parent / new_name
    try:
        p.rename(new_path)
        logger.info(f"Renamed: {p.name} → {new_name}")
        return f"✅ Renombrado: {p.name} → {new_name}"
    except Exception as e:
        return f"❌ Error renombrando: {e}"


@tool
def search_files(directory: str, pattern: str) -> str:
    """Busca archivos que coincidan con un patrón en un directorio.

    Args:
        directory: Ruta del directorio donde buscar.
        pattern: Patrón glob (ej: '*.pdf', '*.jpg', 'factura*').
    """
    err = _check_path(directory)
    if err:
        return err
    p = Path(directory)
    if not p.is_dir():
        return f"❌ No es un directorio: {directory}"

    results = []
    try:
        for match in p.rglob(pattern):
            if len(results) >= 30:
                break
            rel = match.relative_to(p)
            size = match.stat().st_size if match.is_file() else 0
            if size < 1024 * 1024:
                sz = f"{size/1024:.1f} KB"
            else:
                sz = f"{size/1024/1024:.1f} MB"
            results.append(f"{'📄' if match.is_file() else '📁'} {rel} ({sz})")
    except PermissionError:
        return f"⛔ Sin permisos en: {directory}"

    if not results:
        return f"🔍 Sin resultados para '{pattern}' en {directory}"
    header = f"🔍 **{len(results)} resultados** para '{pattern}' en {directory}:\n"
    return header + "\n".join(results)


@tool
def get_file_info(path: str) -> str:
    """Obtiene información detallada de un archivo o carpeta.

    Args:
        path: Ruta absoluta del archivo o carpeta.
    """
    err = _check_path(path)
    if err:
        return err
    p = Path(path)
    if not p.exists():
        return f"❌ No existe: {path}"

    stat = p.stat()
    size = stat.st_size
    if size < 1024:
        sz = f"{size} bytes"
    elif size < 1024 * 1024:
        sz = f"{size/1024:.1f} KB"
    elif size < 1024 ** 3:
        sz = f"{size/1024/1024:.1f} MB"
    else:
        sz = f"{size/1024/1024/1024:.2f} GB"

    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
    created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")

    info = (
        f"📊 **Información de {p.name}**\n"
        f"• Tipo: {'Carpeta' if p.is_dir() else 'Archivo'}\n"
        f"• Tamaño: {sz}\n"
        f"• Modificado: {modified}\n"
        f"• Creado: {created}\n"
        f"• Ruta: {p.resolve()}\n"
    )
    if p.is_dir():
        items = list(p.iterdir())
        info += f"• Contenido: {len(items)} elementos"
    return info


@tool
def create_directory(path: str) -> str:
    """Crea un nuevo directorio (incluyendo padres si es necesario).

    Args:
        path: Ruta absoluta del directorio a crear.
    """
    err = _check_path(path)
    if err:
        return err
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return f"✅ Directorio creado: {path}"
    except Exception as e:
        return f"❌ Error creando directorio: {e}"


@tool
def copy_file(source: str, destination: str) -> str:
    """Copia un archivo a otra ubicación.

    Args:
        source: Ruta absoluta del archivo origen.
        destination: Ruta absoluta del destino.
    """
    for p in [source, destination]:
        err = _check_path(p)
        if err:
            return err
    src = Path(source)
    if not src.exists():
        return f"❌ No existe: {source}"

    dst = Path(destination)
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))
        return f"✅ Copiado: {src.name} → {destination}"
    except Exception as e:
        return f"❌ Error copiando: {e}"


def get_file_tools() -> list:
    """Return all file management tools."""
    return [
        list_directory,
        read_text_file,
        move_file,
        rename_file,
        search_files,
        get_file_info,
        create_directory,
        copy_file,
    ]
