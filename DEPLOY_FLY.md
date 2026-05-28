# Deploy ARIA on Fly.io (24/7 free-tier friendly)

Platform: **Fly.io** — one always-on container (polling Telegram + scheduler).

## Before you start

1. Stop ARIA on your PC (`Ctrl+C` in the terminal running `python run.py`).
2. Push this repo to GitHub (private repo recommended).
3. Install Fly CLI: https://fly.io/docs/hands-on/install-flyctl/
4. Login: `fly auth login`

## One-time Fly setup

```powershell
cd C:\ARIA
fly launch --no-deploy
```

When prompted:

- App name: choose unique name (e.g. `aria-yourname`)
- Region: pick closest (e.g. `mia` for US East)
- Postgres/Redis: **No**
- Deploy now: **No**

Create persistent volume (SQLite + Chroma + Google token files):

```powershell
fly volumes create aria_data --region mia --size 1
```

Confirm `fly.toml` has:

```toml
[mounts]
  source = "aria_data"
  destination = "/data"
```

## Set secrets (copy-paste, replace values)

```powershell
fly secrets set `
  TELEGRAM_TOKEN="YOUR_BOT_TOKEN" `
  TELEGRAM_USER_ID="YOUR_TELEGRAM_NUMERIC_ID" `
  MISTRAL_API_KEY="YOUR_MISTRAL_KEY" `
  MISTRAL_MODEL="mistral-small-latest"
```

Optional (Gmail/Calendar — paste JSON as single-line strings):

```powershell
fly secrets set GOOGLE_TOKEN_JSON='PASTE_token.json_CONTENTS'
fly secrets set GOOGLE_CLIENT_SECRET_JSON='PASTE_client_secret.json_CONTENTS'
```

Optional Firebase:

```powershell
fly secrets set FIREBASE_PROJECT_ID="your-project-id"
fly secrets set FIREBASE_CRED_JSON='PASTE_service_account.json_CONTENTS'
```

Optional morning briefing:

```powershell
fly secrets set MORNING_BRIEFING_ENABLED="true" MORNING_BRIEFING_TIME="08:00" MORNING_BRIEFING_LOCATION="YourCity"
```

## Deploy from GitHub (recommended)

1. Open https://fly.io/dashboard
2. Select your app → **Settings** → connect GitHub repo
3. Enable **Deploy on push** (main branch)

Or deploy manually from PC:

```powershell
fly deploy
```

## Verify

```powershell
fly status
fly logs
```

Open in browser:

```text
https://YOUR_APP_NAME.fly.dev/health
```

Should return: `ok`

Send a Telegram message to your bot — it should reply.

## Start / stop / restart

```powershell
# Stop (scale to 0 — bot offline)
fly scale count 0

# Start again
fly scale count 1

# Restart running machine
fly apps restart

# Live logs
fly logs -a YOUR_APP_NAME
```

## Remove local copy (after cloud works)

1. Confirm Telegram bot answers only from cloud (PC bot stopped).
2. Backup locally:
   - `.env` (secrets)
   - `memory/aria.db`
   - `google_credentials/`
3. Delete project folder from PC if desired — secrets remain in Fly.

## Troubleshooting

| Problem | Fix |
|--------|-----|
| Bot not responding | `fly logs` — check `TELEGRAM_TOKEN`, only one instance (`fly scale count 1`) |
| Conflict / duplicate updates | Stop local `run.py`; webhook cleared automatically on start |
| Gmail fails | Set `GOOGLE_TOKEN_JSON` secret (OAuth browser flow does not work in cloud) |
| App restarts | Check memory; `fly scale memory 512` in fly.toml |
| Health check failing | `curl https://APP.fly.dev/health` |

## Architecture on Fly

```text
Fly Machine (always on)
  ├── HTTP :8080 /health  (keep-alive + health checks)
  ├── Telegram polling (single instance)
  ├── APScheduler (reminders + morning briefing)
  └── /data volume (DB, Chroma, credentials)
```
