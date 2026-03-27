# MVP Startup Plan

## Phase 1 — Core Platform (Target: Working CLI → Agent → Ollama)

### Goal
A developer can run `ai java-dev "create a REST controller"` and get code back.

---

### Step 1: Agent Registry Setup

**Location:** `agent-registry/agents/`

Create initial agents:

`java-dev.json`
```json
{
  "id": "java-dev",
  "name": "Java Developer",
  "model": "qwen3:4b",
  "system": "You are a senior Java developer. Only output clean, working code. No explanation.",
  "mode": "code",
  "temperature": 0.2,
  "maxTokens": 2048,
  "tools": []
}
```

`general.json`
```json
{
  "id": "general",
  "name": "General Assistant",
  "model": "qwen3:4b",
  "system": "You are a helpful assistant.",
  "mode": "chat",
  "temperature": 0.7,
  "maxTokens": 1024,
  "tools": []
}
```

**Done when:** JSON files exist and can be loaded by gateway.

---

### Step 2: Agent Runtime (Python)

**Location:** `agent-runtime/`

Files to create:
- `main.py` — FastAPI app
- `agent_runner.py` — AutoGen execution logic
- `requirements.txt`

**Minimal `/run-agent` endpoint:**
```python
@app.post("/run-agent")
async def run_agent(request: RunAgentRequest):
    agent = AssistantAgent(
        name=request.config["id"],
        system_message=request.config["system"],
        llm_config={"model": request.config["model"], ...}
    )
    # execute and return output
```

**Done when:** `curl localhost:9000/run-agent` returns a response.

---

### Step 3: API Gateway (Spring Boot)

**Location:** `api-gateway/`

Classes to create:
- `AgentController` — `POST /api/agents/{id}/invoke`
- `AgentRegistryService` — load JSON configs
- `AgentRuntimeClient` — HTTP call to Python runtime
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
- [ ] Agent runtime responding on :9000
- [ ] API gateway responding on :8081
- [ ] At least 2 agent configs in registry
- [ ] CLI wrapper working end-to-end
- [ ] No client sends prompts directly to Ollama

---

## Phase 2 — Streaming + Observability

- SSE streaming from gateway to client
- Request/response logging (file or SQLite)
- Agent registry CRUD API (`GET /api/agents`, `POST /api/agents`)
- Runtime health check endpoint

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
cd agent-runtime && uvicorn main:app --port 9000 --reload

# Terminal 3
cd api-gateway && ./mvnw spring-boot:run

# Terminal 4 — test
./cli/ai java-dev "spring boot hello world controller"
```

---

## Validation Tests

```bash
# Health checks
curl http://localhost:9000/health
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
