"""
Export Google OAuth files for Railway environment variables.
Run locally AFTER auth_google.py created google_credentials/token.json.

  python scripts/export_google_token.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREDS_DIR = ROOT / "google_credentials"


def main() -> None:
    token_path = CREDS_DIR / "token.json"
    client_path = CREDS_DIR / "client_secret.json"

    if not token_path.exists():
        print("ERROR: No existe google_credentials/token.json", file=sys.stderr)
        print("Ejecuta primero: python auth_google.py", file=sys.stderr)
        sys.exit(1)

    token = json.loads(token_path.read_text(encoding="utf-8"))
    print("=== GOOGLE_TOKEN_JSON (copia TODO en una linea en Railway) ===\n")
    print(json.dumps(token, ensure_ascii=False))

    if client_path.exists():
        client = json.loads(client_path.read_text(encoding="utf-8"))
        print("\n=== GOOGLE_CLIENT_SECRET_JSON (opcional, para refrescar token) ===\n")
        print(json.dumps(client, ensure_ascii=False))
    else:
        print("\n(client_secret.json no encontrado; solo token exportado)", file=sys.stderr)

    print(
        "\nEn Railway: Variables → GOOGLE_TOKEN_JSON = pega el JSON de arriba (una linea).",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
