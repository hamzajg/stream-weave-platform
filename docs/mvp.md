# MVP Startup Plan

## Phase 1 — Core Platform (Target: Working CLI → Agent → Ollama)

### Goal
A developer can run `ai java-dev "create a REST controller"` and get code back.

---

### Step 1: AutoGen Studio UI (manage agents, models, tools)

Run AutoGen Studio UI and configure your local model provider (Ollama).

Create at least two agents/workflows in Studio:
- `java-dev`
- `general`

**Done when:** Agents/workflows exist in Studio and you can run them in the UI.

---

### Step 2: AutoGen Studio Serve/API (execution endpoint)

Start AutoGen Studio in serve/API mode to expose your selected team/workflow over HTTP so the gateway can invoke it.

**Done when:** Studio serve mode is running and its API docs are reachable (typically at `/docs` on the serve port).

---

### Step 3: API Gateway (Spring Boot)

**Location:** `api-gateway/`

Classes to create:
- `AgentController` — `POST /api/agents/{id}/invoke`
- `StudioClient` (or equivalent) — HTTP call to AutoGen Studio serve/API
- `AgentConfig` — model class

**Done when:** `curl localhost:8081/api/agents/java-dev/invoke` returns a response.

---

### Step 4: CLI Wrapper

**Location:** `cli/ai`

```bash
#!/bin/bash
AGENT=${1:-general}
PROMPT=$2
curl -s http://localhost:8081/api/agents/$AGENT/invoke \
  -H "Content-Type: application/json" \
  -d "{\"input\": \"$PROMPT\"}" | jq -r '.output'
```

```bash
chmod +x cli/ai
# Add to PATH or symlink to /usr/local/bin/ai
```

**Done when:** `./cli/ai java-dev "Hello World"` prints code.

---

### Phase 1 Done Checklist

- [ ] Ollama running with at least one model
- [ ] AutoGen Studio serve/API responding
- [ ] API gateway responding on :8081
- [ ] At least 2 agents/workflows defined in Studio (java-dev, general)
- [ ] CLI wrapper working end-to-end
- [ ] No client sends prompts directly to Ollama

---

## Phase 2 — Streaming + Observability

- SSE streaming from gateway to client
- Request/response logging (file or SQLite)
- Agent/workflow discovery backed by Studio
- Studio health check integration in gateway

---

## Phase 3 — Multi-Agent + Tools

- AutoGen GroupChat for multi-agent workflows
- Tool definitions in agent config (file read, web search, code exec)
- Session context (short-term memory per conversation)
- Multi-turn conversation support

---

## Phase 4 — UI + Distribution

- React frontend (Vite)
- Agent management dashboard
- Conversation history viewer
- Agent marketplace (import/export configs)
- Multi-user with API key auth

---

## Local Dev Startup Order

```bash
# Terminal 1
ollama serve

# Terminal 2
autogenstudio ui --host 127.0.0.1 --port 8082

# Terminal 3
autogenstudio serve --team path/to/team.json --host 127.0.0.1 --port 8084

# Terminal 4
cd api-gateway && ./mvnw spring-boot:run

# Terminal 5 — test
./cli/ai java-dev "spring boot hello world controller"
```

---

## Validation Tests

```bash
# Health checks
curl http://localhost:8084/docs
curl http://localhost:8081/actuator/health

# List agents
curl http://localhost:8081/api/agents

# Invoke agent
curl -X POST http://localhost:8081/api/agents/java-dev/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "java Hello World"}'

# CLI
./cli/ai general "explain REST APIs in 2 sentences"
```
