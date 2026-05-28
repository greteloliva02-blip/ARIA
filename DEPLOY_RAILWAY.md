# Deploy ARIA on Railway (minimal, no Docker)

## 1) Stop local bot first

Only one Telegram instance can run. Stop `python run.py` on your PC.

## 2) Push to GitHub

```powershell
cd C:\ARIA
git add .
git commit -m "Minimal cloud deploy"
git push
```

## 3) Create Railway project

1. Go to https://railway.com and sign in with GitHub
2. **New Project** → **Deploy from GitHub repo** → select your ARIA repo
3. Open the service → **Settings**
4. Set **Start Command**: `python run.py`
5. (Recommended) Disable "Public Networking" if shown — this is a worker bot, not a website

## 4) Set variables (Railway → Variables)

```
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_USER_ID=your_numeric_id
MISTRAL_API_KEY=your_mistral_key
MISTRAL_MODEL=mistral-small-latest
ARIA_MINIMAL=true
DISABLE_CHROMA=true
LOG_LEVEL=INFO
```

Optional Firebase:

```
FIREBASE_PROJECT_ID=your-project
FIREBASE_CRED_JSON={"type":"service_account",...}
```

## 5) Deploy

Railway deploys automatically on git push, or click **Deploy** in dashboard.

## 6) Verify

1. **Deployments** → latest deployment = **Success**
2. **Logs** → look for: `ARIA is running (Telegram polling`
3. Message your bot on Telegram

## Start / stop

- **Stop**: Railway dashboard → service → **Pause** or delete deployment
- **Start**: **Redeploy** or push a commit
- **Logs**: Deployments → View logs

## Common errors

| Error | Fix |
|-------|-----|
| Bot silent | Check `TELEGRAM_TOKEN`, stop local bot |
| Conflict / 409 | Two instances running — stop PC bot |
| MISTRAL_API_KEY missing | Add variable in Railway |
| Build fails on chromadb | Already removed in minimal requirements |
| Crash loop | Open logs, fix env vars, redeploy |
