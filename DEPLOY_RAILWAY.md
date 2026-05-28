# Deploy ARIA on Railway

## Platform
**Railway** — Python worker, no Docker required, GitHub deploy.

## Start command
```
python run.py
```
Set in: **Service → Settings → Deploy → Start Command**

Or use `railway.toml` / `Procfile` (already included).

---

## Step-by-step

### 1. Stop local bot
Only one Telegram instance allowed. Stop `python run.py` on your PC.

### 2. Push to GitHub
```powershell
cd C:\ARIA
git add .
git commit -m "Railway-ready minimal deploy"
git push origin main
```

### 3. Create Railway project
1. https://railway.com → Login with GitHub
2. **New Project** → **Deploy from GitHub repo** → select ARIA repo
3. Wait for first build

### 4. Set environment variables (required — `.env` on your PC is NOT deployed)

Railway **does not** read your local `.env` file. You must paste secrets in the dashboard:

1. Open your project on https://railway.com
2. Click the **service** that runs ARIA (the box connected to your GitHub repo)
3. Tab **Variables**
4. Click **Raw Editor** and paste (use your real values, no quotes):

```env
TELEGRAM_TOKEN=your_full_token_from_botfather
TELEGRAM_USER_ID=your_numeric_telegram_id
MISTRAL_API_KEY=your_mistral_key
MISTRAL_MODEL=mistral-small-latest
DISABLE_CHROMA=true
ARIA_MINIMAL=true
LOG_LEVEL=INFO
```

5. Click **Save** (or Deploy) — Railway should show a new deployment starting.

**Common mistakes**
- Variables added only on your laptop `.env` → container still empty → `TELEGRAM_TOKEN is required`
- Variables on the **Project** but service not linked → open the **service** Variables tab
- Typo in name: must be exactly `TELEGRAM_TOKEN`, not `BOT_TOKEN` or `TELEGRAM_BOT_TOKEN`
- Forgot **Redeploy** after adding variables

Optional:
```env
FIREBASE_PROJECT_ID=
FIREBASE_CRED_JSON=
```

### 5. Configure networking (important)
- **Settings → Networking**
- Railway sets `PORT` automatically for health checks
- App exposes `/health` when `PORT` is set (already handled in `run.py`)

### 6. Redeploy
**Deployments → Redeploy** or push a new commit.

### 7. Verify
**Deployments → View Logs** — look for:
```
Health server listening on 0.0.0.0:...
Mistral LLM ready: mistral-small-latest
Telegram polling active (single instance).
ARIA is running — Telegram polling active
```

Send a message to your bot on Telegram.

---

## Start / stop

| Action | How |
|--------|-----|
| Start | Redeploy, or `git push` |
| Stop | Service → Settings → remove deployment / scale to 0 |
| Restart | Deployments → Restart |
| Logs | Deployments → View Logs |

---

## Troubleshooting crashes

### Crash: `TELEGRAM_TOKEN is required` (repeats every few seconds)

**Cause:** Variables exist only in your PC `.env` file. Railway never receives that file.

**Fix:** Service → **Variables** → Raw Editor → paste `TELEGRAM_TOKEN`, `MISTRAL_API_KEY`, etc. → Save → wait for redeploy. Logs should show `ARIA is running`, not the same error in a loop.

### Crash: `Missing required environment variables` / `FATAL: Missing environment variables`
**Fix:** Add `TELEGRAM_TOKEN` and `MISTRAL_API_KEY` in Railway Variables → Redeploy.

### Crash: `MISTRAL_API_KEY is required`
**Fix:** Same as above. Check for trailing spaces in variable values.

### Crash on build: `firebase-admin` / `chromadb`
**Fix:** Already removed from minimal `requirements.txt`. Commit latest code and redeploy.

### Bot silent / no reply
1. Logs show `Telegram polling active`?
2. Stop local bot (409 conflict)
3. Verify `TELEGRAM_TOKEN` is correct

### Error 409 Conflict
Two instances polling (PC + Railway). Stop local `run.py`.

### `Permission denied` on database
**Fix:** DB now uses `/app/memory/aria.db` inside container (writable). No `/data` volume required.

### Health check failing
Ensure `PORT` is set by Railway (default). Logs must show `Health server listening`.

### Mistral API errors in chat
Bot still replies with fallback message. Check API key quota and `MISTRAL_MODEL` name.

---

## Files used for Railway

| File | Purpose |
|------|---------|
| `run.py` | Entry point |
| `Procfile` | `worker: python run.py` |
| `railway.toml` | Start command + health check |
| `nixpacks.toml` | Nixpacks build hint |
| `requirements.txt` | Minimal dependencies |
| `core/config.py` | All secrets from env |
| `core/health_server.py` | `/health` endpoint |

---

## Ready checklist

- [ ] `TELEGRAM_TOKEN` set in Railway
- [ ] `MISTRAL_API_KEY` set in Railway
- [ ] `TELEGRAM_USER_ID` set (recommended)
- [ ] Local bot stopped
- [ ] Deploy logs show `ARIA is running`
- [ ] Telegram test message works
