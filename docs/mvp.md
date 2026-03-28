# MVP Startup Plan

## Phase 1 — Core Platform (Working CLI → Gateway → AutoGen Studio → Ollama)

### Goal
`./cli/ai java-dev "create a REST controller"` returns code via AutoGen Studio.

---

### Step 1: AutoGen Studio Setup

```bash
pip install autogenstudio
autogenstudio serve --port 8080
```

Open `http://localhost:8080` and:

1. **Add model provider** — point to Ollama:
   - Type: `Ollama`
   - Base URL: `http://localhost:11434`
   - Model: `qwen3:4b`

2. **Create agents:**
   - Name: `Java Developer`
   - System message: `You are a senior Java developer. Only output clean, working code. No explanation.`
   - Model: `qwen3:4b`

   - Name: `General Assistant`
   - System message: `You are a helpful, concise assistant.`
   - Model: `qwen3:4b`

3. **Create teams** (one per agent for Phase 1):
   - Team: `Java Developer Team` → agent: `Java Developer`
   - Team: `General Team` → agent: `General Assistant`

4. Note the team names exactly — they must match the registry entries.

**Done when:** Studio UI shows agents and teams, and a test run in the UI returns output.

---

### Step 2: Agent Registry

Update `agent-registry/agents/` to map IDs to Studio team names:

`java-dev.json`
```json
{
  "id": "java-dev",
  "studioTeam": "Java Developer Team",
  "description": "Senior Java developer — outputs code only",
  "tags": ["code", "java"]
}
```

`general.json`
```json
{
  "id": "general",
  "studioTeam": "General Team",
  "description": "General purpose assistant",
  "tags": ["chat"]
}
```

**Done when:** JSON files exist and team names match Studio exactly.

---

### Step 3: API Gateway (Spring Boot)

Services to implement:

**`AgentRegistryService`** — reads JSON files from `agent-registry/agents/`

**`StudioClient`** — WebClient wrapper:
- `Mono<String> resolveTeamId(String teamName)` — calls `GET /api/agents`, matches by name
- `Mono<String> runAgent(String teamId, String input)` — calls `POST /api/runs`

**`AgentResolverService`** — registry-first, Studio fallback:
```
findById(agentId)
  → registry hit? use studioTeam
  → miss? call StudioClient.listAgents(), match name
  → still miss? throw AgentNotFoundException → 404
```

**`AgentController`** — exposes:
- `GET /api/agents`
- `GET /api/agents/{id}`
- `POST /api/agents/{id}/invoke`

**Done when:** `curl localhost:8081/api/agents/java-dev/invoke` returns a real Studio response.

---

### Step 4: CLI Wrapper

```bash
chmod +x cli/ai
./cli/ai java-dev "hello world in java"
# Should print code
./cli/ai general "explain REST in 2 sentences"
# Should print explanation
```

**Done when:** Both calls return correct output end-to-end.

---

### Phase 1 Checklist

- [ ] Ollama running with `qwen3:4b`
- [ ] AutoGen Studio running on :8080
- [ ] At least 2 agents + 2 teams defined in Studio UI
- [ ] Registry entries match Studio team names exactly
- [ ] Gateway resolves and invokes via registry-first path
- [ ] Gateway falls back to Studio list when registry misses
- [ ] Gateway returns 404 for unknown agents
- [ ] CLI wrapper works end-to-end for all defined agents

---

### Local Dev Startup Order

```bash
# Terminal 1
ollama serve

# Terminal 2
autogenstudio serve --port 8080

# Terminal 3
cd api-gateway && ./mvnw spring-boot:run

# Terminal 4 — smoke test
curl http://localhost:8081/api/agents
curl -X POST http://localhost:8081/api/agents/java-dev/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "hello world in java"}'
./cli/ai java-dev "spring boot rest controller"
```

---

## Phase 2 — Streaming + Observability

- SSE streaming: gateway proxies Studio chunked response → SSE to client
- Request/response logging to SQLite
- Registry CRUD API (`POST /api/agents` to register new IDs)
- Gateway startup health check — poll Studio `/api/health` before accepting traffic

---

## Phase 3 — Multi-Agent + Tools

- Multi-agent teams built in Studio UI (planner + executor patterns)
- Session ID support — pass `session_id` to Studio for multi-turn memory
- Tool execution via Studio tool definitions (file read, web search, code exec)
- Expose session API: `POST /api/agents/{id}/sessions`

---

## Phase 4 — UI + Distribution

- React frontend (Vite) consuming `/api/agents` endpoints
- Agent management dashboard (list, test, monitor)
- Conversation history viewer
- Multi-user support with API key auth in gateway
- Agent export/import (share registry entries)

---

## Validation Tests

```bash
# Studio health
curl http://localhost:8080/api/health

# Gateway health
curl http://localhost:8081/actuator/health

# List agents (from registry)
curl http://localhost:8081/api/agents

# Invoke — registry path
curl -X POST http://localhost:8081/api/agents/java-dev/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "java Hello World"}'

# Invoke — should Studio fallback (no registry entry)
curl -X POST http://localhost:8081/api/agents/general-assistant/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "what is REST?"}'

# Unknown agent — expect 404
curl -X POST http://localhost:8081/api/agents/does-not-exist/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'

# CLI
./cli/ai java-dev "spring boot hello world controller"
./cli/ai general "explain dependency injection in 2 sentences"
```
