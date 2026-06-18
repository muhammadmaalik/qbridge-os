# Deploy the API to Render

Live frontend: **https://qbridge-os.vercel.app**  
Live API: **https://qbridge-os.onrender.com**

## Current status check

Open in your browser:

- https://qbridge-os.onrender.com/health → `"status": "ok"`
- https://qbridge-os.onrender.com/api/v1/system/version → `"auth_routes": true`
- https://qbridge-os.onrender.com/health → `"smtp_configured": true` **(required for login)**

If `smtp_configured` is `false`, login will fail until you complete **Step 2** below.

---

## Step 1 — Render service settings

1. Open **https://dashboard.render.com** → your **qbridge-os** web service.
2. **Settings → Build & Deploy**

   | Setting | Value |
   |---------|--------|
   | Root Directory | *(blank)* |
   | Branch | `main` |
   | Build Command | `bash render-build.sh` |
   | Start Command | `HOST=0.0.0.0 python run_api.py` |
   | Health Check Path | `/health` |

3. **Manual Deploy → Deploy latest commit** if you changed settings.

---

## Step 2 — Enable login emails (required)

Registration works without email, but **sign-in sends a 6-digit OTP** — you must configure outbound email on Render.

### Option A — Brevo (recommended, ~3 minutes)

1. Sign up free at **https://www.brevo.com** and verify your email.
2. **SMTP & API → API Keys → Generate a new API key**.
3. In Render → **qbridge-os → Environment**, add:

   | Key | Value |
   |-----|--------|
   | `QBRIDGE_BREVO_API_KEY` | your Brevo API key (`xkeysib-...`) |
   | `QBRIDGE_BREVO_SENDER_EMAIL` | the same email you verified in Brevo |

4. Click **Save Changes** (Render redeploys automatically).

### Option B — Gmail SMTP

1. Turn on **2-Step Verification** on your Google account.
2. Create an **App Password**: https://myaccount.google.com/apppasswords
3. In Render → **Environment**, add:

   | Key | Value |
   |-----|--------|
   | `QBRIDGE_SMTP_HOST` | `smtp.gmail.com` |
   | `QBRIDGE_SMTP_PORT` | `587` |
   | `QBRIDGE_SMTP_USER` | `you@gmail.com` |
   | `QBRIDGE_SMTP_PASSWORD` | 16-character app password (no spaces) |
   | `QBRIDGE_SMTP_FROM` | `you@gmail.com` |
   | `QBRIDGE_SMTP_TLS` | `1` |

4. **Save Changes** and wait for redeploy (~2 min).

### Other required environment variables

| Key | Value |
|-----|--------|
| `QBRIDGE_CORS_ORIGINS` | `https://qbridge-os.vercel.app,http://127.0.0.1:3000` |
| `QBRIDGE_JWT_SECRET` | long random string |
| `QBRIDGE_FORCE_MEMORY_DB` | `1` |
| `QBRIDGE_SKIP_PQC_VERIFY` | `1` |

---

## Step 3 — Verify email is working

After redeploy, open:

**https://qbridge-os.onrender.com/health**

You should see `"smtp_configured": true`.

In Render **Logs**, on startup you should see:

```
Email OTP: configured (brevo)
```
or
```
Email OTP: configured (smtp)
```

Then test **https://qbridge-os.vercel.app/login**:

1. Register (or sign in if already registered)
2. Check inbox + spam for the 6-digit code
3. Enter OTP → dashboard

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| “Email OTP is not configured” on login page | Add Brevo or Gmail vars in Render Environment, save, wait for redeploy |
| `smtp_configured: false` in `/health` | Env vars missing or typo in key names (must start with `QBRIDGE_`) |
| 503 on login after adding Gmail | Wrong app password; use App Password, not your normal Gmail password |
| 503 with Brevo | `QBRIDGE_BREVO_SENDER_EMAIL` must be verified in Brevo |
| Cold start / timeout | Free tier sleeps ~30–60s; retry or use `.\start-local.ps1` for demos |
| Auth API not found (404) | Old deploy — redeploy latest `main` commit |

---

## Vercel frontend

Environment variable:

- `NEXT_PUBLIC_API_BASE` = `https://qbridge-os.onrender.com`

Already set in `frontend/vercel.json`; redeploy Vercel if you change it.

---

## Local demo backup

```powershell
cd qbridge-os
copy .env.example .env
# Edit .env with Brevo or Gmail settings
.\start-local.ps1
```

Open http://127.0.0.1:3000
