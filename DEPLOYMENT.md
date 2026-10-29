# Quick Deployment Guide for SIH Submission

You can deploy this application publicly so the Smart India Hackathon evaluators can test your live demo link.

Choose the option that fits your remaining time:

---

## ⚡ Option 1: Instant Live Public URL via Cloudflare Tunnel / Ngrok (Fastest: 2 Minutes)
If you have **less than 30 minutes** before the deadline and already have the app running locally on port 5173 and 8000:

### Using Cloudflare Tunnel (100% Free, No Account Needed):
In PowerShell:
```powershell
# In a new terminal window:
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:5173
```
- Cloudflare will print a live public link like:  
  `https://your-random-subdomain.trycloudflare.com`
- Anyone (including SIH judges) can open that link and use the complete app live!

### Or Using Localtunnel (Zero Install, Uses npx):
```powershell
npx localtunnel --port 5173
```

---

## 🚀 Option 2: 1-Click Full Cloud Deployment via Render (Recommended: ~6 Minutes)
The repository includes a ready-to-use `render.yaml` blueprint.

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "feat: complete AICTE dashboard with query copilot"
   git push origin main
   ```
2. **Go to Render**:
   - Open [render.com](https://render.com) and sign in with GitHub.
   - Click **New +** $\rightarrow$ **Blueprint**.
   - Select your `SIH26264-Complains-Dashboard` repository.
   - Click **Apply**.
3. **What Render does automatically**:
   - Deploys the Python FastAPI backend service (`aicte-dashboard-api`), seeds the database, and exposes the `/api` routes.
   - Builds and deploys the React frontend static site (`aicte-dashboard-web`), connecting it to the backend.
   - Provides an HTTPS live link (e.g. `https://aicte-dashboard-web.onrender.com`).

---

## 🌐 Option 3: Vercel (Frontend) + Render (Backend)

### A. Deploy Backend on Render:
1. On Render, click **New +** $\rightarrow$ **Web Service**.
2. Connect your repo and set:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variable**: `DATABASE_URL=sqlite:///./aicte.db`
3. Copy your live backend URL (e.g., `https://aicte-api.onrender.com`).

### B. Deploy Frontend on Vercel:
1. Open [vercel.com](https://vercel.com) and import your GitHub repo.
2. Set:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Environment Variable**:
     - `VITE_API_BASE_URL` = `https://aicte-api.onrender.com`
     - `VITE_USE_MOCKS` = `false`
3. Click **Deploy**. Vercel will build and provide your live link (e.g., `https://aicte-dashboard.vercel.app`) in ~40 seconds.

