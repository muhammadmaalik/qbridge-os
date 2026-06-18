# Deploy the API to Render (fix “Auth API not found”)

The live frontend at **https://qbridge-os.vercel.app** calls **https://qbridge-os.onrender.com**.
If login shows *“Auth API not found”*, Render is still serving an **old build** from before auth was added.

## One-time fix (5 minutes)

1. Open **https://dashboard.render.com** and sign in.
2. Open your **qbridge-os** web service (or create one — see below).
3. **Settings → Build & Deploy**
   - **Root Directory:** leave blank (repo root)
   - **Build Command:** `bash render-build.sh`
   - **Start Command:** `HOST=0.0.0.0 python run_api.py`
   - **Health Check Path:** `/health`
4. **Environment** — add (required for login emails):

   | Key | Example |
   |-----|---------|
   | `QBRIDGE_SMTP_HOST` | `smtp.gmail.com` |
   | `QBRIDGE_SMTP_PORT` | `587` |
   | `QBRIDGE_SMTP_USER` | `you@gmail.com` |
   | `QBRIDGE_SMTP_PASSWORD` | Gmail **App Password** (16 chars) |
   | `QBRIDGE_SMTP_FROM` | `you@gmail.com` |
   | `QBRIDGE_SMTP_TLS` | `1` |
   | `QBRIDGE_CORS_ORIGINS` | `https://qbridge-os.vercel.app,http://127.0.0.1:3000` |
   | `QBRIDGE_JWT_SECRET` | long random string |
   | `QBRIDGE_FORCE_MEMORY_DB` | `1` |

5. Click **Manual Deploy → Deploy latest commit**.
6. Wait 8–15 minutes (first build installs scientific Python packages).
7. Verify in a browser:
   - https://qbridge-os.onrender.com/health → `"status": "ok"`
   - https://qbridge-os.onrender.com/api/v1/system/version → `"auth_routes": true`

Then reload **https://qbridge-os.vercel.app/login** and register / sign in.

## Create service from GitHub (if none exists)

1. Render → **New +** → **Web Service**
2. Connect repo **muhammadmaalik/qbridge-os**
3. Use the build/start commands above
4. Plan: **Free** (cold starts ~30–60s on first request)

## Vercel frontend

Ensure **Environment Variable**:

- `NEXT_PUBLIC_API_BASE` = `https://qbridge-os.onrender.com`

Redeploy Vercel after changing it.

## Investor demo offline backup

If Render is cold-starting during a meeting:

```powershell
cd qbridge-os
.\start-local.ps1
```

Open http://127.0.0.1:3000 — chemistry and dashboard work without cloud API cold start.
