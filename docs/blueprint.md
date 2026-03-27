# System Blueprint

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   VERTICAL 2: Clients                    │
│         CLI  │  Aider  │  Web App  │  Mobile  │  Bot    │
└──────────────────────────┬──────────────────────────────┘
                           │  HTTP / SSE
┌──────────────────────────▼──────────────────────────────┐
│              VERTICAL 1: Local AI Platform               │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │          API Gateway  :8081  (Spring Boot)       │   │
│  │   POST /api/agents/{id}/invoke                   │   │
│  │   GET  /api/agents                               │   │
│  │   GET  /api/agents/{id}                          │   │
│  └──────────────────┬──────────────────────────────┘   │
│                     │  HTTP  (internal)                 │
│  ┌──────────────────▼──────────────────────────────┐   │
│  │         AutoGen Studio Serve  (HTTP API)         │   │
│  │   (serves teams/workflows as endpoints)          │   │
│  └──────────────────┬──────────────────────────────┘   │
│                     │                                  │
│  ┌──────────────────▼──────────────────────────────┐   │
│  │          Ollama  :11434  (model provider)        │   │
│  │   qwen3:4b  │  llama3  │  codellama  │  ...      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              AutoGen Studio UI + DB              │   │
│  │   agents/models/tools/workflows (managed in UI)  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Component Responsibilities

### 2.1 API Gateway (Spring Boot :8081)

| Responsibility | Detail |
|---------------|--------|
| Expose REST API | `/api/agents/{id}/invoke` |
| Resolve agent/workflow | Resolve via AutoGen Studio (serve/API) |
| Route to execution | Forward request to Studio serve endpoint |
| Handle streaming | SSE response wrapping |
| Error handling | 404 on unknown agent/workflow, 502 on Studio failure |

**Key controllers:**
- `AgentController` — invoke endpoint
- `AgentRegistryController` — list/get agents

---

### 2.2 AutoGen Studio (UI + Serve/API)

| Responsibility | Detail |
|---------------|--------|
| Manage agents/models/tools | UI + persistence (DB) |
| Define workflows/teams | Saved and versionable (export/import) |
| Serve execution API | Expose workflows/teams over HTTP for integration |
| Execute prompts | Via AutoGen → Ollama (or any supported model provider) |

**Simple execution path (Phase 1):**
```
Gateway request
  → Studio serve endpoint
  → AutoGen executes workflow/team
  → returns normalized output/events
```

---

### 2.3 CLI Wrapper

```bash
#!/bin/bash
# Usage: ai <agentId> "<prompt>"
AGENT=$1
PROMPT=$2

curl -s http://localhost:8081/api/agents/$AGENT/invoke \
  -H "Content-Type: application/json" \
  -d "{\"input\": \"$PROMPT\"}" | jq -r '.output'
```

---

## 3. Data Flow — Single Agent Invocation

```
1. Client sends:
   POST /api/agents/java-dev/invoke
   { "input": "java Hello World!" }

2. Gateway resolves the agent/workflow mapping via Studio (or a served team/workflow export).

3. Gateway calls AutoGen Studio serve/API:
   POST http://localhost:<studio-serve-port>/<workflow-endpoint>
   { "input": "..." }

4. Studio executes via AutoGen and calls Ollama:
   workflow/team → model client → Ollama

5. Studio returns output/events.

6. Gateway wraps and returns to client:
   { "output": "...", "meta": { "agentId": "java-dev" } }
```

---

## 4. Streaming Flow (SSE)

```
Client → Gateway (SSE connection open)
Gateway → Runtime (chunked HTTP)
Runtime → Ollama (stream: true)

Runtime emits chunks → Gateway forwards as SSE:
  data: {"delta": "public"}
  data: {"delta": " class"}
  data: {"done": true}
```

---

## 5. Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| API Gateway | Spring Boot | 3.x |
| Agent management + execution API | AutoGen Studio | latest |
| Orchestration | AutoGen | via Studio |
| Model Provider | Ollama | latest |
| Agent Storage | Studio DB (SQLite default) | - |
| CLI | Bash + curl + jq | - |

---

## 6. Port Map

| Service | Port |
|---------|------|
| API Gateway | 8081 |
| AutoGen Studio UI | configurable |
| AutoGen Studio Serve/API | configurable |
| Ollama | 11434 |

---

## 7. Extension Points

| Future Need | Extension |
|------------|-----------|
| Tool execution | Studio-managed tools attached to agents/workflows |
| Memory | Add session context store (Redis) |
| Multi-agent | Studio workflows/teams (AutoGen GroupChat under the hood) |
| Auth | API key middleware in gateway |
| UI | AutoGen Studio UI (admin) + optional product UI later |
