# Shop-AI

A web-based AI inventory and sales assistant for small shops. Snap a photo of your stock, and the AI counts it. Log sales, get low-stock alerts, and track revenue — all from your phone browser.

Built as a test bench for the core features. WhatsApp integration will be layered on top once the logic is solid.

## Stack

- **Backend:** FastAPI (Python) on Render
- **Frontend:** Plain HTML/CSS/JS on Vercel
- **AI:** Google Gemini (vision + text)
- **Database:** Supabase (Postgres)

## Features

- [x] Photo → AI inventory count (Gemini Vision)
- [x] Manual product add/edit/delete
- [x] Sale logging with auto stock deduction
- [x] Low-stock alerts (≤5 units)
- [x] Stats dashboard (total products, stock, revenue)
- [ ] Frontend web app (in progress)
- [ ] WhatsApp integration (future)
- [ ] Customer-facing bot (future)

## Deploy (Backend — Render)

### 1. Supabase Setup
- Create a new project at [supabase.com](https://supabase.com)
- Open **SQL Editor** and run the contents of `supabase_schema.sql`
- Go to **Settings → API** and copy:
  - `Project URL`
  - `service_role` key (keep this secret)

### 2. Gemini API Key
- Go to [aistudio.google.com](https://aistudio.google.com)
- Sign in → Get API key → copy

### 3. Render Setup
- New → Web Service
- Connect GitHub repo `shop-ai`
- Runtime: **Python 3**
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Instance Type: **Free**

### 4. Environment Variables (Render)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
GEMINI_API_KEY=your_gemini_api_key


## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Health check |
| GET | `/api/products` | List all products |
| POST | `/api/product` | Create a product |
| PATCH | `/api/product/{id}` | Update a product |
| DELETE | `/api/product/{id}` | Delete a product |
| POST | `/api/sale` | Record a sale (auto-deduct) |
| GET | `/api/alerts` | Low-stock items (≤5) |
| POST | `/api/scan` | Upload photo → AI counts products |
| GET | `/api/stats` | Dashboard statistics |

## Local Development

```bash
pip install -r requirements.txt
# create .env with real values (copy from .env.example)
uvicorn main:app --reload

Repo Structure
shop-ai/
├── main.py                 # FastAPI backend
├── requirements.txt        # Python deps
├── supabase_schema.sql     # DB schema (run once in Supabase)
├── .env.example            # Env var template
├── .gitignore              # Blocks .env from commit
└── README.md
Built by
Dexter (Okeke Chukwudubem) — Dexter Digital
