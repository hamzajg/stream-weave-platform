# StreamWeave Platform — Enterprise AI Agentic Workflow Platform

> A fully-integrated platform enabling business specialists across manufacturing, finance, insurance, healthcare, ecommerce, transportation, and agriculture to build, deploy, and manage AI agentic workflows without writing code.

[![Built by Tanoshii Computing](https://img.shields.io/badge/Built%20by-Tanoshii%20Computing-00d4ff?style=flat-square)](https://tanoshii-computing.com)
[![Community](https://img.shields.io/badge/Community-Discord-5865F2?style=flat-square)](https://tanoshii-computing.com/community)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

---

## Overview

StreamWeave is an **enterprise-grade AI Agentic workflow platform** designed for business specialists who need to migrate their operations to AI-powered automation. Built with Python FastAPI and React, it provides a visual workflow builder, enterprise onboarding, and seamless integration with Microsoft AutoGen Studio.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  StreamWeave Platform Architecture                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Client (Web Portal / REST API / CLI)                                       │
│        │                                                                    │
│        │  HTTP / SSE / WebSocket                                             │
│        ▼                                                                    │
│  FastAPI Gateway :8000                                                      │
│        │                                                                    │
│        ├─ /                    → React Landing Page (Static)               │
│        ├─ /api/health          → Health check                               │
│        ├─ /api/auth/*          → Authentication (JWT)                       │
│        ├─ /api/orgs/*          → Organization management                    │
│        ├─ /api/workflows/*     → Workflow CRUD + execution                  │
│        ├─ /api/agents/*        → AutoGen Studio proxy                       │
│        └─ /api/runs/*          → Execution monitoring + SSE                 │
│                                                                              │
│        ├─ Actor System (Asyncio)                                            │
│        │   ├── MessageBus (async queue)                                      │
│        │   ├── SupervisorActor (orchestration)                              │
│        │   └── WorkerActor (agent executor)                                 │
│        │                                                                    │
│        └─ SQLAlchemy ORM (SQLite dev / PostgreSQL prod)                     │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  External Integrations                                                        │
│  ├── Microsoft AutoGen Studio :8080  (control plane)                        │
│  └── Ollama :11434                   (local LLM runtime)                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### 🎨 Visual Workflow Builder
- Drag-and-drop workflow designer (ReactFlow)
- Connect AI agents, conditions, and actions visually
- No coding required — designed for business specialists
- Real-time validation and preview

### 🏢 Enterprise Onboarding
- Multi-tenant organization support
- Role-based access control (Owner, Editor, Viewer)
- API key management for programmatic access
- Audit logs and compliance features

### 🤖 AI Agent Orchestration
- Single-agent invocation for simple tasks
- Multi-agent task orchestration via actor model
- Config-first + LLM fallback planning
- Real-time execution monitoring with SSE streaming

### 🔄 AutoGen Studio Integration
- Seamless integration with Microsoft AutoGen Studio
- Leverage AutoGen's agent capabilities
- Local AI execution via Ollama
- Secure, self-hosted deployment

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional, for production)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/hamzajg/stream-weave-platform.git
cd stream-weave-platform

# 2. Install Python dependencies
pip3 install -r requirements.txt

# 3. Install and build frontend
cd webapp
npm install
npm run build
cd ..

# 4. Run the backend
uvicorn app.main:app --reload --port 8000
```

### Docker (Production)

```bash
# Start with PostgreSQL
docker-compose up -d

# View logs
docker-compose logs -f app
```

Visit `http://localhost:8000` to see the landing page.

---

## Project Structure

```
stream-weave-platform/
├── app/                          # Python FastAPI Backend
│   ├── api/                      # API route handlers
│   │   ├── health.py             # Health check endpoints
│   │   ├── auth.py               # Authentication (future)
│   │   ├── workflows.py          # Workflow management (future)
│   │   └── agents.py             # AutoGen proxy (future)
│   ├── models/                   # SQLAlchemy models
│   ├── static/                   # Frontend build output
│   ├── config.py                 # Pydantic settings
│   ├── database.py               # SQLAlchemy setup
│   └── main.py                   # FastAPI entry point
├── webapp/                       # React Frontend
│   ├── src/
│   │   ├── components/           # React components
│   │   ├── styles/               # Theme CSS
│   │   └── App.tsx               # Main app
│   ├── vite.config.ts            # Build config
│   └── tailwind.config.js        # Theme configuration
├── docs/                         # Documentation
│   ├── ux-analysis-report.md
│   ├── theme-specification-improved.md
│   └── blueprint.md
├── Dockerfile                    # Production image
├── docker-compose.yml            # Full stack orchestration
└── requirements.txt              # Python dependencies
```

---

## API Endpoints

### Current (Iteration 1)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page |
| `/health` | GET | Simple health check |
| `/api/health` | GET | Detailed health status |
| `/api/ready` | GET | Readiness check |

### Planned (Future Iterations)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/*` | Various | Authentication |
| `/api/orgs/*` | Various | Organization management |
| `/api/workflows/*` | Various | Workflow CRUD |
| `/api/agents/*` | Various | Agent proxy |
| `/api/runs/*` | GET | Execution monitoring |

---

## Design System

StreamWeave uses the **improved Tanoshii Computing design system**:

### Colors
- **Background Primary**: `#0c1220` — Deep navy black
- **Background Secondary**: `#121b2e` — Elevated surfaces
- **Accent (Cyan)**: `#00d4ff` — Primary action color
- **Text Primary**: `#f0f4f8` — Headlines
- **Text Secondary**: `#a8b8c8` — Body text

### Typography
- **Display**: `Orbitron` — Brand/logo only
- **Body**: `Inter` — All UI text

### Features
- ✅ Glassmorphism navigation
- ✅ Blueprint grid background
- ✅ 44px touch targets
- ✅ Full focus states (accessibility)
- ✅ Reduced motion support

[View full theme specification →](docs/theme-specification-improved.md)

---

## Development Roadmap

| Iteration | Scope | Status |
|-----------|-------|--------|
| **1** | Landing page + Python backend + Docker | ✅ Complete |
| **2** | Auth system (register/login), protected routes | 🔄 Planned |
| **3** | Frontend portal (dashboard, org switcher) | 🔄 Planned |
| **4** | MS AutoGen Studio integration (full hosted) | 🔄 Planned |
| **5** | Visual workflow builder (ReactFlow) | 🔄 Planned |
| **6** | Workflow runners, execution engine, SSE | 🔄 Planned |

---

## Community & Support

- 🌐 **Website**: [tanoshii-computing.com](https://tanoshii-computing.com)
- 💬 **Community**: [tanoshii-computing.com/community](https://tanoshii-computing.com/community)
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-org/stream-weave-platform/issues)
- 📧 **Email**: support@tanoshii-computing.com

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with 💙 by <a href="https://tanoshii-computing.com">Tanoshii Computing</a></sub>
</p>
