"""
ARIA - Script de Setup Automatico
Instala dependencias y verifica la configuracion.
"""
import subprocess
import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main():
    print("=" * 55)
    print("  ARIA - Setup Automatico")
    print("=" * 55)
    print()

    project_root = Path(__file__).parent

    # -- 1. Check Python version
    v = sys.version_info
    print(f"Python {v.major}.{v.minor}.{v.micro}")
    if v.major < 3 or v.minor < 10:
        print("[ERROR] Se requiere Python 3.10 o superior.")
        sys.exit(1)
    print("   [OK] Version compatible")
    print()

    # -- 2. Install dependencies
    print("Instalando dependencias...")
    req = project_root / "requirements.txt"
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        capture_output=False,
    )
    if result.returncode != 0:
        print("[WARN] Algunas dependencias podrian no haberse instalado.")
    else:
        print("   [OK] Dependencias instaladas")
    print()

    # -- 3. Check .env
    env_file = project_root / ".env"
    all_ok = True
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8")
        checks = {
            "TELEGRAM_TOKEN": "Token de Telegram",
            "MISTRAL_API_KEY": "API Key de Mistral",
        }
        for key, label in checks.items():
            line = [l for l in content.splitlines() if l.startswith(f"{key}=")]
            if line:
                val = line[0].split("=", 1)[1].strip()
                if val:
                    print(f"   [OK] {label}: configurado")
                else:
                    print(f"   [WARN] {label}: VACIO - edita .env")
                    all_ok = False
            else:
                print(f"   [ERROR] {label}: no encontrado en .env")
                all_ok = False
    else:
        print("[ERROR] Archivo .env no encontrado")
        all_ok = False
    print()

    # -- 4. Create directories
    dirs = [
        project_root / "memory",
        project_root / "logs",
        project_root / "data" / "notes",
        project_root / "data" / "pdfs",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("[OK] Directorios creados: memory/, logs/, data/notes/, data/pdfs/")
    print()

    # -- Done
    print("=" * 55)
    if all_ok:
        print("  [OK] ARIA esta lista!")
        print()
        print("  Para iniciar ARIA ejecuta:")
        print(f"    python {project_root / 'run.py'}")
    else:
        print("  [WARN] Revisa los items marcados arriba.")
        print("  Edita el archivo .env y vuelve a ejecutar setup.")
    print("=" * 55)


if __name__ == "__main__":
    main()
