# Tree of Life AI - Backend API

Integrative Health Intelligence Platform combining 9 medical traditions.

## 🚀 Quick Deploy to Railway

This structure is optimized for Railway deployment with zero configuration needed.

### Prerequisites
- Railway account
- GitHub account
- Anthropic API key
- OpenAI API key (for embeddings)
- Pinecone API key (optional)

### Deploy Steps

**1. Push to GitHub:**
```bash
git init
git add -A
git commit -m "Initial commit - Tree of Life AI backend"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/Tree-of-Life-AI.git
git push -u origin main
```

**2. Deploy to Railway:**
- Go to railway.app
- Click "New Project"
- Select "Deploy from GitHub repo"
- Choose this repo
- Railway will auto-detect Dockerfile and deploy!

**3. Add Environment Variables in Railway:**
```
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY
OPENAI_API_KEY=sk-YOUR-KEY
PINECONE_API_KEY=pcsk_YOUR-KEY
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=your-secret-key-min-32-characters
ENVIRONMENT=production
ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

**4. Generate Domain:**
- Railway → Settings → Generate Domain
- Copy the URL

**5. Test:**
Visit: `https://your-railway-url.up.railway.app/health`

Should return:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## 🏗️ Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your keys

# Run database
docker-compose up -d postgres redis

# Run app
uvicorn app.main:app --reload
```

Visit: http://localhost:8000/docs

## 📁 Project Structure

```
├── railway.json          # Railway configuration
├── Dockerfile            # Docker build instructions
├── requirements.txt      # Python dependencies
├── app/
│   ├── main.py          # FastAPI application
│   ├── config.py        # Settings & environment
│   ├── database.py      # Database connection
│   ├── api/             # API routes
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── utils/           # Utilities
└── alembic/             # Database migrations
```

## 🌟 Features

- **9 Medical Traditions:** Western, Ayurveda, TCM, Herbal, Homeopathy, Chiropractic, Nutrition, Vibrational, Physical Therapy
- **AI-Powered:** Anthropic Claude Sonnet 4.5
- **RAG:** Pinecone vector database for knowledge retrieval
- **Emergency Detection:** Automatic identification of critical symptoms
- **HIPAA-Compliant:** Encrypted data, secure architecture
- **Real-time Chat:** WebSocket support for streaming responses

## 📚 API Documentation

Once running, visit:
- **Swagger UI:** `/docs`
- **ReDoc:** `/redoc`

## 🔒 Security

- JWT authentication
- Password hashing (bcrypt)
- API rate limiting
- CORS protection
- Input validation

## 📞 Support

For issues or questions, please open a GitHub issue.

---

Built with ❤️ for integrative health
