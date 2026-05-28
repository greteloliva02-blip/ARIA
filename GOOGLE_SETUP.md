# Gmail y Google Calendar en ARIA

ARIA ya tiene el código de Gmail y Calendar. Solo necesitas **autorizar Google una vez en tu PC** y **copiar el token a Railway**.

## Resumen del flujo

```
Tu PC (una vez)          Railway (24/7)
───────────────          ──────────────
auth_google.py    →    GOOGLE_TOKEN_JSON
(client_secret)   →    GOOGLE_CLIENT_SECRET_JSON (opcional)
```

En la nube **no** se puede abrir el navegador OAuth; el token se genera en local.

---

## Paso 1 — Google Cloud Console

1. Entra a https://console.cloud.google.com/
2. Crea o elige un proyecto.
3. **APIs y servicios → Biblioteca** → activa:
   - **Gmail API**
   - **Google Calendar API**
4. **APIs y servicios → Pantalla de consentimiento OAuth**
   - Tipo: **Externo**
   - Añade tu correo como usuario de prueba
5. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente OAuth**
   - Tipo: **Aplicación de escritorio**
   - Descarga el JSON
6. Renombra el archivo a `client_secret.json` y colócalo en:

```
C:\ARIA\google_credentials\client_secret.json
```

---

## Paso 2 — Autorizar en tu PC (solo una vez)

En PowerShell:

```powershell
cd C:\ARIA
pip install -r requirements.txt
python auth_google.py
```

- Se abre el navegador → inicia sesión con la cuenta de Gmail/Calendar que quieres usar.
- Acepta los permisos.
- Se crea `google_credentials\token.json`.

Prueba local (opcional):

```powershell
python run.py
```

En Telegram: *"¿tengo correos sin leer?"* o *"¿qué tengo en el calendario esta semana?"*

---

## Paso 3 — Subir el token a Railway

Exporta el JSON en una línea:

```powershell
python scripts/export_google_token.py
```

Copia la salida de **GOOGLE_TOKEN_JSON**.

En Railway → tu servicio → **Variables**:

| Variable | Valor |
|----------|--------|
| `GOOGLE_TOKEN_JSON` | Pega el JSON completo del token (una línea) |
| `GOOGLE_CLIENT_SECRET_JSON` | (Opcional) JSON de `client_secret.json` — ayuda a refrescar el token |
| `ARIA_DATA_DIR` | `/data` si ya usas esa ruta para la base de datos |

**Redeploy** y revisa logs:

```
Google OK — Gmail + Calendar enabled.
Loaded tools: ['web_search', 'read_emails', 'send_email', 'list_calendar_events', 'create_calendar_event']
```

---

## Acciones que entiende el bot

| Acción | Uso en Telegram (ejemplos) |
|--------|----------------------------|
| `read_emails` | "lee mis correos sin leer", "correos de hoy" |
| `send_email` | "envía un correo a juan@..." |
| `list_calendar_events` | "qué tengo en el calendario", "eventos de mañana" |
| `create_calendar_event` | "crea reunión mañana 10am por 1 hora" |
| `web_search` | "busca en internet..." |

---

## Problemas frecuentes

### "Gmail no autenticado" / solo web_search en logs
- Falta `GOOGLE_TOKEN_JSON` en Railway o el JSON está mal pegado (debe ser una sola línea válida).
- Vuelve a ejecutar `auth_google.py` y exporta de nuevo.

### Token expirado
- Ejecuta otra vez `python auth_google.py` en el PC.
- Actualiza `GOOGLE_TOKEN_JSON` en Railway y redeploy.

### En local funciona, en Railway no
- Confirma redeploy después de guardar variables.
- Pega también `GOOGLE_CLIENT_SECRET_JSON` si el refresh falla.

### Desactivar Google temporalmente
Variable `DISABLE_GOOGLE=true` en Railway.

---

## Seguridad

- **Nunca** subas `token.json` ni `client_secret.json` a GitHub (ya están en `.gitignore`).
- Solo usa variables de Railway para los JSON.
- Si filtraste el token, revócalo en https://myaccount.google.com/permissions
