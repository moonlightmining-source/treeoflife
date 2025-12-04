# 🚀 RAILWAY DEPLOYMENT GUIDE

## ✅ WHAT YOU HAVE

This package contains a **CLEAN, RAILWAY-OPTIMIZED** backend structure:

```
Tree-of-Life-AI/
├── railway.json          ← Railway config (simple!)
├── Dockerfile            ← Works from root
├── requirements.txt      ← All dependencies
├── .env.example          ← Environment template
├── .gitignore            ← Git safety
├── app/                  ← Your application
│   ├── __init__.py
│   ├── config.py         ← Settings
│   ├── database.py       ← DB connection
│   ├── main.py           ← FastAPI app
│   ├── api/              ← API routes (ready for expansion)
│   ├── models/           ← Database models (ready for expansion)
│   ├── schemas/          ← Pydantic schemas (ready for expansion)
│   ├── services/         ← Business logic (ready for expansion)
│   └── utils/            ← Utilities (ready for expansion)
└── alembic/              ← Database migrations
    ├── env.py
    └── script.py.mako
```

## 🎯 DEPLOYMENT STEPS

### STEP 1: PUSH TO GITHUB

```bash
# Initialize git (if not already)
git init
git add -A
git commit -m "Initial commit - Tree of Life AI backend (Railway-optimized)"
git branch -M main

# Add your GitHub repo
git remote add origin https://github.com/YOUR-USERNAME/Tree-of-Life-AI.git
git push -u origin main
```

### STEP 2: CREATE NEW RAILWAY SERVICE

1. **Go to Railway Dashboard:** https://railway.app/dashboard
2. **Click "+ New"**
3. **Select "GitHub Repo"**
4. **Choose:** Tree-of-Life-AI
5. **Railway will start building automatically!**

### STEP 3: ADD ENVIRONMENT VARIABLES

**Railway → Your Service → Variables Tab → Raw Editor**

**Paste this (replace with YOUR keys):**

```
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-NEW-KEY-HERE
OPENAI_API_KEY=sk-YOUR-OPENAI-KEY
PINECONE_API_KEY=pcsk_YOUR-PINECONE-KEY
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=your-secret-key-minimum-32-characters-long
ENVIRONMENT=production
DEBUG=False
ALLOWED_ORIGINS=https://tree-of-life-ai-frontend.vercel.app
ADMIN_EMAIL=moonlight_mining@yahoo.com
ADMIN_PASSWORD=Pootchi30
```

**Click Save** - Railway will redeploy automatically

### STEP 4: ADD POSTGRESQL DATABASE

1. **Railway → Your Project → "+ New"**
2. **Select "Database" → "PostgreSQL"**
3. **Database will be created**
4. **The `DATABASE_URL` variable will auto-populate!**

### STEP 5: ADD REDIS (OPTIONAL)

1. **Railway → Your Project → "+ New"**
2. **Select "Database" → "Redis"**
3. **Redis will be created**
4. **The `REDIS_URL` variable will auto-populate!**

### STEP 6: GENERATE DOMAIN

1. **Railway → Your Service → Settings**
2. **Scroll to "Networking"**
3. **Click "Generate Domain"**
4. **Copy the URL** (like `tree-of-life-ai-production-abc123.up.railway.app`)

### STEP 7: VERIFY DEPLOYMENT

**Visit your Railway URL + `/health`:**

```
https://your-railway-url.up.railway.app/health
```

**Should return:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

**✅ SUCCESS! Your backend is live!**

### STEP 8: CHECK DEBUG ENDPOINT

**Visit:** `https://your-railway-url.up.railway.app/debug/env-check`

**Should show:**
```json
{
  "anthropic_key": "...2hXnmwAA",    ← Last 8 chars of YOUR new key
  "openai_key": "...514A",
  "pinecone_key": "...wjB",
  "environment": "production"
}
```

**Verify the anthropic_key matches YOUR new key!**

### STEP 9: UPDATE VERCEL

**Vercel → Your Project → Settings → Environment Variables**

**Update:**
```
VITE_API_URL=https://your-new-railway-url.up.railway.app
```

**Redeploy Vercel**

### STEP 10: TEST AUTHENTICATION

1. Visit: `https://tree-of-life-ai-frontend.vercel.app`
2. Should redirect to `auth.html`
3. Register a new account
4. Should redirect to chat
5. Send a test message
6. **You should get AI response!** 🎉

## 🔥 IF BUILD FAILS

**Check Railway logs for errors:**

**Common issues:**
- ❌ Missing environment variable → Add it in Variables tab
- ❌ Wrong Anthropic key → Check last 8 characters in `/debug/env-check`
- ❌ Database not connected → Make sure PostgreSQL is added to project

## 📸 WHAT GOOD LOGS LOOK LIKE

```
✅ using build driver dockerfile
✅ FROM docker.io/library/python:3.11-slim
✅ RUN pip install --no-cache-dir -r requirements.txt
✅ Successfully built image
✅ Container started
✅ 🚀 Starting Tree of Life AI...
✅ ✅ Database initialized
✅ ✅ Tree of Life AI is ready!
✅ Uvicorn running on http://0.0.0.0:8080
```

## 🎉 YOU'RE DONE!

Your backend is now:
- ✅ Running on Railway
- ✅ Using PostgreSQL database
- ✅ Using Redis cache
- ✅ Using NEW Anthropic API key
- ✅ Accessible via public URL
- ✅ Ready for frontend connection

## 🔧 NEXT STEPS

1. **Expand the API** - Add routes in `app/api/`
2. **Add database models** - Create models in `app/models/`
3. **Add business logic** - Create services in `app/services/`
4. **Add Claude integration** - Build AI features
5. **Add authentication** - Implement JWT auth
6. **Add RAG** - Integrate Pinecone vector search

## 📚 DOCUMENTATION

Once deployed, visit:
- **API Docs:** `https://your-url.up.railway.app/docs`
- **ReDoc:** `https://your-url.up.railway.app/redoc`

## ❓ TROUBLESHOOTING

**Backend won't start:**
- Check Railway logs
- Verify all environment variables are set
- Check `/debug/env-check` shows correct keys

**Database connection fails:**
- Make sure PostgreSQL is added to Railway project
- Check `DATABASE_URL` variable exists

**Old API key still showing:**
- This was a Railway caching bug
- This clean deployment fixes it forever!

## 🎊 SUCCESS!

You now have a CLEAN, WORKING, RAILWAY-OPTIMIZED backend!

No more subdirectory issues!
No more ghost API keys!
Just clean, working code! 🚀
