# StreamWeave Platform - Quick Start Guide

## Iteration 1: Landing Page + Python Backend

This iteration includes:
- ✅ React + TypeScript + TailwindCSS landing page
- ✅ Python FastAPI backend
- ✅ Static file serving (frontend built to `app/static/`)
- ✅ Health check API endpoint
- ✅ Docker & Docker Compose for production
- ✅ Improved UX theme (glassmorphism, unified colors)

---

## Project Structure

```
stream-weave-platform/
├── app/                          # Python FastAPI Backend
│   ├── api/
│   │   └── health.py             # Health check endpoints
│   ├── models/
│   │   └── __init__.py           # SQLAlchemy models (placeholder)
│   ├── static/                   # Frontend build output
│   │   ├── index.html            # Landing page
│   │   └── assets/               # Built JS/CSS assets
│   ├── __init__.py
│   ├── config.py                 # Pydantic settings
│   ├── database.py               # SQLAlchemy setup
│   └── main.py                   # FastAPI entry point
├── webapp/                       # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx        # Glassmorphism navigation
│   │   │   ├── Hero.tsx          # Hero section
│   │   │   ├── Features.tsx      # Feature cards
│   │   │   └── Footer.tsx        # Footer
│   │   ├── styles/
│   │   │   └── theme.css         # Design tokens
│   │   ├── App.tsx               # Main app
│   │   └── index.css             # Tailwind + theme import
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js        # Custom theme config
│   ├── postcss.config.js
│   └── vite.config.ts            # Build to ../app/static
├── Dockerfile                    # Production image
├── docker-compose.yml            # Full stack orchestration
├── requirements.txt              # Python dependencies
└── QUICKSTART.md                 # This file
```

---

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for production)

### 1. Install Python Dependencies

```bash
cd /Users/hamzajguerim/Downloads/stream-weave-platform
pip3 install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd webapp
npm install
```

### 3. Build Frontend

```bash
npm run build
```

This builds the React app to `app/static/` where Python serves it.

### 4. Run Backend (Development)

```bash
cd ..
uvicorn app.main:app --reload --port 8000
```

The backend will:
- Serve the landing page at `http://localhost:8000/`
- Provide API docs at `http://localhost:8000/api/docs` (if DEBUG=true)
- Health check at `http://localhost:8000/api/health`

---

## Production Deployment

### Using Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop
docker-compose down
```

Services:
- **App**: FastAPI backend on port 8000
- **Database**: PostgreSQL 15

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./streamweave.db` | Database connection string |
| `SECRET_KEY` | `your-secret-key-change-in-production` | JWT secret |
| `DEBUG` | `false` | Debug mode |
| `AUTOGEN_STUDIO_URL` | `http://localhost:8080` | AutoGen Studio URL |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama URL |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page (static files) |
| `/health` | GET | Simple health check |
| `/api/health` | GET | Detailed health status |
| `/api/ready` | GET | Readiness check for K8s |

---

## Design System

The landing page uses the **improved UX theme**:

### Colors
- Background Primary: `#0c1220`
- Background Secondary: `#121b2e`
- Accent (Cyan): `#00d4ff`
- Text Primary: `#f0f4f8`
- Text Secondary: `#a8b8c8`

### Typography
- Display: `Orbitron` (brand/logo only)
- Body: `Inter` (all UI text)

### Features
- ✅ Glassmorphism navigation (`backdrop-filter: blur(16px)`)
- ✅ 8px border radius (modern but professional)
- ✅ 44px minimum touch targets
- ✅ Full focus states for accessibility
- ✅ Reduced motion support
- ✅ High contrast mode support
- ✅ Subtle grid background pattern

---

## Next Iterations

| Iteration | Scope |
|-----------|-------|
| Iteration 2 | Auth system (register/login), protected routes |
| Iteration 3 | Frontend portal (dashboard, org switcher) |
| Iteration 4 | MS AutoGen Studio integration (full hosted) |
| Iteration 5 | Visual workflow builder (ReactFlow) |
| Iteration 6 | Workflow runners, execution engine, SSE streams |

---

## Troubleshooting

### Frontend build fails
```bash
cd webapp
rm -rf node_modules package-lock.json
npm install --force
npm run build
```

### Python dependencies issues
```bash
pip3 install --upgrade pip
pip3 install -r requirements.txt --force-reinstall
```

### Port 8000 already in use
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9
# Or use different port
uvicorn app.main:app --reload --port 8001
```
