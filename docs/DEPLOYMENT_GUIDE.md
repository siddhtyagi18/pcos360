# PCOS360 — Production Deployment Guide

## 1. Infrastructure Overview

- **Backend Hosting**: Render Web Service (FastAPI running Uvicorn workers).
- **Database**: Supabase Managed PostgreSQL 17 (AWS Tokyo).
- **Web Frontend**: Vercel / Netlify / Render Static Site.
- **Mobile Distribution**: Signed standalone APK via GitHub Releases / Internal Distribution.

---

## 2. Backend Deployment on Render

1. Create a new **Web Service** on [Render.com](https://render.com).
2. Connect your Git repository.
3. Set the following build and start configurations:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Configure **Environment Variables** in Render Dashboard:
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `False`
   - `SECRET_KEY`: `<secure-random-64-character-hex-string>`
   - `DATABASE_URL`: `postgresql+psycopg2://postgres.<project>:<password>@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres?sslmode=require`
   - `GEMINI_API_KEY`: `<your-production-gemini-key>`
   - `GEMINI_MODEL`: `gemini-flash-lite-latest`
   - `GROQ_API_KEY`: `<optional-backup-key>`
   - `GROQ_MODEL`: `llama-3.3-70b-versatile`
   - `BACKEND_CORS_ORIGINS`: `["https://pcos360.vercel.app","https://pcos360.onrender.com"]`
   - `TRUST_PROXY_HEADERS`: `True`
5. Verify health:
   ```bash
   curl -s https://pcos360-backend.onrender.com/api/health
   ```

---

## 3. Database Deployment on Supabase

1. Create a Supabase project in the region closest to your users.
2. In the Supabase SQL Editor, run schema migrations to create all tables (`users`, `user_sessions`, `health_profiles`, `menstrual_cycles`, `daily_symptoms`, `lifestyle_logs`, `lab_reports`, `clinical_records`).
3. Ensure the foreign keys specify `ON DELETE CASCADE`.
4. Ensure `lab_reports.created_at` defaults to `now()`:
   ```sql
   ALTER TABLE lab_reports ALTER COLUMN created_at SET DEFAULT now();
   ```

---

## 4. Web Frontend Deployment (Vercel / Static Host)

1. Connect the repository to Vercel.
2. Set Root Directory: `frontend`
3. Framework Preset: `Vite`
4. Build Command: `npm run build`
5. Output Directory: `dist`
6. Environment Variables:
   - `VITE_API_URL`: `https://pcos360-backend.onrender.com/api`

---

## 5. Deployment Recovery & Rollback Procedures

1. **Database Recovery**: Supabase automated daily backups and Point-In-Time Recovery (PITR) allow restoring state to any second within the retention window.
2. **Backend Rollback**: Render allows instant one-click rollback to any previous successful deployment commit.
3. **Cold Start Handling**: If the Render backend spins down due to free-tier inactivity, the frontend and mobile apps show a graceful loading indicator during the initial wake-up ping (`GET /api/health`).

