import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

def main():
    print("="*60)
    print(" Iniciando autenticacion de Google (OAuth2)")
    print("="*60)
    
    creds_dir = Path(__file__).resolve().parent / "google_credentials"
    client_secret_path = creds_dir / "client_secret.json"
    token_path = creds_dir / "token.json"
    
    if not client_secret_path.exists():
        print(f"[ERROR] No se encontro {client_secret_path}")
        return
        
    print("\nGenerando URL de autorizacion...")
    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secret_path), SCOPES
    )
    
    # Esto abrira el navegador o imprimira la URL
    creds = flow.run_local_server(port=0, prompt="consent")
    
    with open(token_path, "w") as f:
        f.write(creds.to_json())
        
    print("\n[OK] Autenticacion exitosa. Token guardado en:")
    print(token_path)
    print("Ya puedes cerrar esta ventana y volver a Telegram.")

if __name__ == "__main__":
    main()
