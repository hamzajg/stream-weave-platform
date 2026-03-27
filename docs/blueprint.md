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
│                     │  HTTP  (internal)                  │
│  ┌──────────────────▼──────────────────────────────┐   │
│  │       Agent Runtime  :9000  (FastAPI + AutoGen)  │   │
│  │   POST /run-agent                                │   │
│  └──────────────────┬──────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────────┐   │
│  │          Ollama  :11434  (model provider)        │   │
│  │   qwen3:4b  │  llama3  │  codellama  │  ...      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │         Agent Registry  (JSON / SQLite)          │   │
│  │   agent configs: id, model, system, tools        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Component Responsibilities

### 2.1 API Gateway (Spring Boot :8081)

| Responsibility | Detail |
|---------------|--------|
| Expose REST API | `/api/agents/{id}/invoke` |
| Resolve agent config | Load from registry by ID |
| Route to runtime | Forward to Python service |
| Handle streaming | SSE response wrapping |
| Error handling | 404 on unknown agent, 502 on runtime failure |

**Key controllers:**
- `AgentController` — invoke endpoint
- `AgentRegistryController` — list/get agents

---

### 2.2 Agent Runtime (Python FastAPI :9000)

| Responsibility | Detail |
|---------------|--------|
| Receive agent execution requests | `POST /run-agent` |
| Instantiate AutoGen agent | From passed config |
| Execute prompt | Via AutoGen → Ollama |
| Return normalized output | `{ output, tokens }` |

**Simple execution path (Phase 1):**
```
receive {agentId, input, config}
  → build AssistantAgent(system_message=config.system)
  → call Ollama via AutoGen
  → return { output: response_text }
```

---

### 2.3 Agent Registry

**Phase 1:** JSON files in `agent-registry/agents/`

**Schema:**
```json
{
  "id": "java-dev",
  "name": "Java Developer",
  "model": "qwen3:4b",
  "system": "You are a senior Java developer. Only output code.",
  "mode": "code",
  "temperature": 0.2,
  "maxTokens": 2048,
  "tools": []
}
```

**Phase 2:** SQLite with CRUD API

---

### 2.4 CLI Wrapper

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

2. Gateway resolves agent config from registry:
   { id: "java-dev", model: "qwen3:4b", system: "..." }

3. Gateway calls runtime:
   POST http://localhost:9000/run-agent
   { "input": "...", "config": { ... } }

4. Runtime builds AutoGen agent and calls Ollama:
   AssistantAgent(system_message=config.system)
   → ollama.generate(model, prompt)

5. Runtime returns:
   { "output": "public class HelloWorld {...}", "tokens": 120 }

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
| Agent Runtime | FastAPI | 0.110+ |
| Orchestration | AutoGen | 0.2.x |
| Model Provider | Ollama | latest |
| Agent Storage | JSON → SQLite | Phase 1 → 2 |
| CLI | Bash + curl + jq | - |

---

## 6. Port Map

| Service | Port |
|---------|------|
| API Gateway | 8081 |
| Agent Runtime | 9000 |
| Ollama | 11434 |

---

## 7. Extension Points

| Future Need | Extension |
|------------|-----------|
| Tool execution | Add `tools[]` to agent config + runtime tool handler |
| Memory | Add session context store (Redis) |
| Multi-agent | AutoGen GroupChat in runtime |
| Auth | API key middleware in gateway |
| UI | React frontend calling same `/api/agents` endpoints |
