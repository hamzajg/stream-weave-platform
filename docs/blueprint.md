# System Blueprint

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                   VERTICAL 2 — Clients                        │
│      CLI  │  Aider  │  Web App  │  Mobile  │  Bot / Agent    │
└─────────────────────────┬────────────────────────────────────┘
                          │  HTTP / SSE
┌─────────────────────────▼────────────────────────────────────┐
│                VERTICAL 1 — Local AI Platform                 │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │       API Gateway  :8081  (Spring Boot)               │  │
│  │   POST /api/agents/{id}/invoke                        │  │
│  │   GET  /api/agents                                    │  │
│  │   GET  /api/agents/{id}                               │  │
│  └────────────┬────────────────────────┬─────────────────┘  │
│               │                        │                     │
│    registry   │                        │ invoke run          │
│    lookup     │                        │ (internal HTTP)     │
│               ▼                        ▼                     │
│  ┌────────────────────┐  ┌─────────────────────────────┐   │
│  │  Agent Registry    │  │  AutoGen Studio  :8080       │   │
│  │  (JSON / SQLite)   │  │                             │   │
│  │                    │  │  ┌──────────┐ ┌──────────┐  │   │
│  │  id → studioTeam   │  │  │ Studio   │ │ REST API │  │   │
│  │  mapping           │  │  │ UI       │ │ /api/runs│  │   │
│  │                    │  │  └──────────┘ └────┬─────┘  │   │
│  └────────────────────┘  └───────────────────┬──────────┘  │
│                                              │              │
│                              ┌───────────────▼────────┐    │
│                              │   Ollama  :11434        │    │
│                              │   qwen3:4b · llama3     │    │
│                              └────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component Responsibilities

### 2.1 API Gateway (Spring Boot :8081)

| Responsibility | Detail |
|---------------|--------|
| Public REST API | `/api/agents/{id}/invoke`, `/api/agents` |
| Agent resolution | Registry-first → Studio fallback |
| Studio bridge | Translates invoke request → AutoGen Studio `/api/runs` |
| SSE streaming | Proxies Studio streaming response to client |
| Error surface | 404 for unresolved agents, 502 for Studio failures |

**Services:**
- `AgentResolverService` — orchestrates registry + Studio fallback
- `AgentRegistryService` — reads JSON config files
- `StudioClient` — WebClient wrapper for AutoGen Studio API

---

### 2.2 AutoGen Studio (:8080)

Launched via:
```bash
autogenstudio serve --port 8080
```

| Capability | Detail |
|-----------|--------|
| Agent/team builder | Visual UI at `http://localhost:8080` |
| REST API | `POST /api/runs` — execute a team/agent |
| Agent listing | `GET /api/agents` — used by gateway fallback |
| Session management | Built-in, per run |
| Model config | Points to Ollama via model provider settings |

**Studio API used by gateway:**

```
POST http://localhost:8080/api/runs
{
  "message": "java Hello World!",
  "team_id": "<studio-team-uuid>"
}

GET http://localhost:8080/api/agents
→ [ { "id": "...", "name": "Java Developer Team", ... } ]
```

---

### 2.3 Agent Registry

**Location:** `agent-registry/agents/`

**Purpose:** Maps stable client-facing IDs to AutoGen Studio team names/IDs.

**Schema:**
```json
{
  "id": "java-dev",
  "studioTeam": "Java Developer Team",
  "description": "Senior Java developer — outputs code only",
  "tags": ["code", "java"]
}
```

**Resolution logic:**
1. Gateway reads `java-dev.json` → gets `studioTeam: "Java Developer Team"`
2. Gateway calls Studio API to resolve team name → team UUID
3. Gateway calls `POST /api/runs` with that UUID

**Registry is the source of truth for agent IDs.**  
**Studio is the source of truth for agent execution configs.**

---

### 2.4 Agent Resolution — Detailed Flow

```
POST /api/agents/java-dev/invoke  {input: "..."}
          │
          ▼
AgentResolverService
          │
          ├─ Step 1: AgentRegistryService.findById("java-dev")
          │    Found → AgentRef { studioTeam: "Java Developer Team" }
          │    Not found → Step 2
          │
          ├─ Step 2: StudioClient.listAgents()
          │    Match name "java-dev" or "Java Developer Team"
          │    Found → use Studio agent ID
          │    Not found → throw 404
          │
          ▼
StudioClient.runAgent(teamId, input)
     POST http://localhost:8080/api/runs
          │
          ▼
     AutoGen Studio executes → Ollama
          │
          ▼
     Response mapped → { output, meta }
          │
          ▼
     Client ← HTTP / SSE
```

---

### 2.5 CLI Wrapper

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

## 3. Gateway Code Structure

```
api-gateway/src/main/java/com/localai/gateway/
├── controller/
│   └── AgentController.java          # REST endpoints
├── service/
│   ├── AgentResolverService.java     # registry-first, Studio fallback
│   ├── AgentRegistryService.java     # reads JSON registry files
│   └── StudioClient.java             # WebClient → AutoGen Studio API
├── model/
│   ├── AgentRef.java                 # registry entry POJO
│   ├── InvokeRequest.java            # client request body
│   ├── InvokeResponse.java           # client response body
│   └── StudioRun.java                # Studio /api/runs request/response
└── config/
    └── WebClientConfig.java          # WebClient bean
```

---

## 4. Streaming Flow (SSE)

```
Client opens SSE connection:
  POST /api/agents/java-dev/invoke  { stream: true }

Gateway:
  Calls StudioClient.runAgentStream(teamId, input)
  Studio returns chunked HTTP stream
  Gateway wraps each chunk as SSE event:
    data: {"delta": "public class"}
    data: {"delta": " HelloWorld"}
    data: {"done": true}

Client reads SSE stream and renders tokens as they arrive.
```

---

## 5. Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| API Gateway | Spring Boot | 3.2.x |
| Control plane | AutoGen Studio | 0.4.x |
| Model provider | Ollama | latest |
| Agent storage | JSON → SQLite (Phase 2) | — |
| HTTP client | Spring WebFlux WebClient | — |
| CLI | Bash + curl + jq | — |

---

## 6. Port Map

| Service | Port | Notes |
|---------|------|-------|
| AutoGen Studio UI + API | 8080 | Must start before gateway |
| API Gateway | 8081 | Public surface for all clients |
| Ollama | 11434 | Internal only — never exposed to clients |

---

## 8. Extension Points

| Future Need | Extension |
|------------|-----------|
| Tool execution | Define tools in Studio UI — no gateway change |
| Multi-agent teams | Build teams in Studio UI — no gateway change |
| Memory / sessions | Pass `session_id` to Studio `/api/runs` |
| Auth | API key middleware in Spring Boot gateway |
| UI | React frontend hitting same `/api/agents` endpoints |
| New model | Add model in Studio settings — no code change |
