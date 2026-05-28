"""
ARIA — Herramientas de Automatización Local
Abrir programas, ejecutar comandos, información del sistema.
"""
import os
import subprocess
import platform
from pathlib import Path

from langchain_core.tools import tool

from core.config import Config
from core.logger import get_logger

logger = get_logger("tools.computer")
_config = Config()

# Commands that are always blocked for safety
_BLOCKED_COMMANDS = [
    "format", "del /s", "rd /s", "rmdir /s",
    "shutdown", "restart", "reg delete",
    "diskpart", "cipher /w",
]


@tool
def run_command(command: str) -> str:
    """Ejecuta un comando en la terminal de Windows (PowerShell).
    PRECAUCIÓN: Solo para comandos seguros. Comandos destructivos están bloqueados.

    Args:
        command: Comando a ejecutar (ej: 'dir C:\\Users', 'ipconfig').
    """
    # Safety check
    cmd_lower = command.lower().strip()
    for blocked in _BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return f"⛔ Comando bloqueado por seguridad: contiene '{blocked}'"

    logger.info(f"Executing command: {command}")
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path.home()),
        )
        output = result.stdout.strip() or result.stderr.strip() or "(sin salida)"
        # Truncate very long output
        if len(output) > 3000:
            output = output[:3000] + "\n\n... (salida truncada)"

        status = "✅" if result.returncode == 0 else "⚠️"
        return f"{status} **Comando:** `{command}`\n```\n{output}\n```"

    except subprocess.TimeoutExpired:
        return f"⏰ Comando excedió el tiempo límite (30s): {command}"
    except Exception as e:
        logger.error(f"Command execution error: {e}")
        return f"❌ Error ejecutando comando: {e}"


@tool
def open_program(program_name: str) -> str:
    """Abre un programa o aplicación en Windows.

    Args:
        program_name: Nombre del programa (ej: 'notepad', 'chrome', 'explorer', 'calculator').
    """
    # Map common names to executables
    programs = {
        "notepad": "notepad.exe",
        "bloc de notas": "notepad.exe",
        "calculadora": "calc.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "explorador": "explorer.exe",
        "explorer": "explorer.exe",
        "chrome": "chrome.exe",
        "navegador": "chrome.exe",
        "paint": "mspaint.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "powershell": "powershell.exe",
        "task manager": "taskmgr.exe",
        "administrador de tareas": "taskmgr.exe",
    }

    exe = programs.get(program_name.lower().strip(), program_name)

    try:
        subprocess.Popen(
            exe,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"Opened program: {exe}")
        return f"✅ Programa abierto: {program_name}"
    except Exception as e:
        return f"❌ Error abriendo '{program_name}': {e}"


@tool
def system_info() -> str:
    """Obtiene información del sistema: CPU, RAM, disco, OS."""
    try:
        import psutil

        # OS
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"

        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # RAM
        mem = psutil.virtual_memory()
        ram_total = mem.total / (1024 ** 3)
        ram_used = mem.used / (1024 ** 3)
        ram_pct = mem.percent

        # Disk
        disks = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                total_gb = usage.total / (1024 ** 3)
                free_gb = usage.free / (1024 ** 3)
                disks.append(
                    f"  💾 {part.device} — "
                    f"{free_gb:.1f} GB libres / {total_gb:.1f} GB total "
                    f"({usage.percent}% usado)"
                )
            except PermissionError:
                continue

        # Battery
        battery = psutil.sensors_battery()
        bat_str = ""
        if battery:
            plug = "🔌" if battery.power_plugged else "🔋"
            bat_str = f"\n{plug} Batería: {battery.percent}%"

        return (
            f"💻 **Sistema**\n"
            f"• OS: {os_info}\n"
            f"• CPU: {cpu_count} cores ({cpu_percent}% uso)\n"
            f"• RAM: {ram_used:.1f} / {ram_total:.1f} GB ({ram_pct}%)\n"
            f"\n📀 **Discos:**\n" + "\n".join(disks) +
            bat_str
        )
    except ImportError:
        return "❌ Módulo psutil no instalado."
    except Exception as e:
        return f"❌ Error obteniendo info del sistema: {e}"


@tool
def list_running_processes(filter_name: str = "") -> str:
    """Lista los procesos en ejecución, opcionalmente filtrados por nombre.

    Args:
        filter_name: Nombre parcial para filtrar (ej: 'chrome'). Vacío = top 20 por RAM.
    """
    try:
        import psutil

        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
            try:
                info = p.info
                if filter_name and filter_name.lower() not in info["name"].lower():
                    continue
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by memory usage
        procs.sort(key=lambda x: x.get("memory_percent", 0) or 0, reverse=True)
        procs = procs[:20]

        if not procs:
            return f"🔍 No se encontraron procesos{' con ' + repr(filter_name) if filter_name else ''}."

        lines = [f"⚙️ **Procesos {'(' + filter_name + ')' if filter_name else 'top 20 por RAM'}:**\n"]
        for p in procs:
            mem = p.get("memory_percent", 0) or 0
            lines.append(f"• {p['name']} (PID {p['pid']}) — RAM {mem:.1f}%")

        return "\n".join(lines)

    except ImportError:
        return "❌ Módulo psutil no instalado."
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def kill_process(process_name: str) -> str:
    """Cierra/mata un proceso por su nombre. Requiere confirmación del usuario.

    Args:
        process_name: Nombre del proceso a cerrar (ej: 'notepad.exe').
    """
    try:
        import psutil

        killed = 0
        for p in psutil.process_iter(["name"]):
            try:
                if p.info["name"] and p.info["name"].lower() == process_name.lower():
                    p.terminate()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            return f"✅ Cerrados {killed} proceso(s) de '{process_name}'"
        return f"🔍 No se encontró el proceso: {process_name}"

    except ImportError:
        return "❌ Módulo psutil no instalado."
    except Exception as e:
        return f"❌ Error: {e}"


def get_computer_tools() -> list:
    """Return all computer automation tools."""
    return [
        run_command,
        open_program,
        system_info,
        list_running_processes,
        kill_process,
    ]
