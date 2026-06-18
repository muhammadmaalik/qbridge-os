# Deploy the API to Render

Live frontend: **https://qbridge-os.vercel.app**  
Live API: **https://qbridge-os.onrender.com**

## Verify deployment

- https://qbridge-os.onrender.com/health → `"status": "ok"`
- https://qbridge-os.onrender.com/api/v1/system/version` → `"auth_routes": true`, `"user_store": "postgres"` or `"sqlite"`

Login is **email + password only** (no OTP email required).

---

## Render service settings

| Setting | Value |
|---------|--------|
| Root Directory | *(blank)* |
| Branch | `main` |
| Build Command | `bash render-build.sh` |
| Start Command | `HOST=0.0.0.0 python run_api.py` |
| Health Check Path | `/health` |

## Environment variables

| Key | Value |
|-----|--------|
| `DATABASE_URL` | From Render PostgreSQL (recommended) |
| `QBRIDGE_CORS_ORIGINS` | `https://qbridge-os.vercel.app,http://127.0.0.1:3000` |
| `QBRIDGE_JWT_SECRET` | long random string |
| `QBRIDGE_MAX_REGS_PER_IP` | `3` |

**Do not set** `QBRIDGE_FORCE_MEMORY_DB=1` in production — that wipes accounts on restart.

### Add PostgreSQL on Render

1. Render dashboard → **New +** → **PostgreSQL**
2. Copy the **Internal Database URL**
3. On your **qbridge-os** web service → **Environment** → add `DATABASE_URL` with that value
4. Redeploy

If Postgres is unavailable, the API falls back to SQLite locally or on disk.

---

## Test login

1. https://qbridge-os.vercel.app/login
2. Register with email + password
3. Sign in — you should go straight to the dashboard

Each IP address can register at most **3 accounts**.

---

## Local dev

```powershell
cd qbridge-os
.\start-local.ps1
```

Open http://127.0.0.1:3000
