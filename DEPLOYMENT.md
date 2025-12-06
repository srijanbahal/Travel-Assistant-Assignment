# 🚀 Deployment Guide

This guide explains how to deploy the **InviGrid Travel Assistant**. The application consists of two parts:
1. **Backend**: FastAPI (Python) - Recommended host: **Render**
2. **Frontend**: Next.js (React) - Recommended host: **Vercel**

---

## 📦 1. Database Configuration (Crucial)

You asked: *"my app uses static table so i guess current version of travel.db will work right ?"*

**Answer**: Yes, for a **Demo**, you can commit the `travel.db` file to your GitHub repository.
- The `init_db.py` script seeds it with static data (flights, hotels).
- **Note**: On serverless platforms (like Render/Vercel), the filesystem is *ephemeral*. This means new bookings saved to SQLite will **reset** every time the server restarts.
- **For Demo**: This is perfectly fine. The static flights will always be there.
- **For Production**: You would swap SQLite for PostgreSQL (Render provides a free instance).

**Action**: Ensure `data/travel.db` is **NOT** inside `.gitignore` so it gets pushed to GitHub.

---

## 🐍 2. Deploying Backend (Render)

1. **Push your code** to a GitHub repository.
2. Sign up at [Render.com](https://render.com).
3. Click **New +** → **Web Service**.
4. Connect your GitHub repo.
5. **Settings**:
   - **Name**: `invigrid-backend`
   - **Root Directory**: `.` (leave empty)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.api:app --host 0.0.0.0 --port $PORT`
6. **Environment Variables**:
   - `GROQ_API_KEY`: `your_key_here`
   - `PYTHON_VERSION`: `3.11.0` (Recommended)
7. Click **Deploy**.
8. **Copy the URL** (e.g., `https://invigrid-backend.onrender.com`).

---

## ⚛️ 3. Deploying Frontend (Vercel)

1. Sign up at [Vercel.com](https://vercel.com).
2. Click **Add New** → **Project**.
3. Import the same GitHub repo.
4. **Settings**:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend` (Important! Click Edit and select the `frontend` folder)
5. **Environment Variables**:
   - `NEXT_PUBLIC_API_URL`: The Backend URL from Step 2 (e.g., `https://invigrid-backend.onrender.com`)
     - *Note: Do not add a trailing slash `/`*
6. Click **Deploy**.

---

## 🔗 4. Connecting Them

The Frontend needs to know where the Backend is.

1. **In `frontend/lib/api.ts`**, ensure the code uses the environment variable:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace("http", "ws"); 
```

2. By setting `NEXT_PUBLIC_API_URL` in Vercel, the frontend will automatically use the live backend for both REST and WebSocket connections.

---

## ✅ Verification

1. Open the Vercel App URL.
2. Type "Show me flights to Delhi".
3. Check if responses appear (Backend is working).
4. Test "New Chat" button correctly resets session.
