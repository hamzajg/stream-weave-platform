# MVP Startup Plan

## Phase 1 — Multi-Agent Task Mesh (builds on single-agent base)

### Goal
`./cli/ai task code-review "review this method..."` runs two agents in sequence, passes context between them, and returns a synthesised result.

---

### Step 1: AutoGen Studio — add required teams

Open `http://localhost:8080` and create these teams (if not already done):

| Team name | Agent | System prompt |
|-----------|-------|---------------|
| Java Developer Team | Java Developer | You are a senior Java developer. Only output clean, working code. No explanation. |
| Python Developer Team | Python Developer | You are a senior Python developer. Only output clean, working code. No explanation. |
| General Team | General Assistant | You are a helpful, concise assistant. |
| Reviewer Team | Reviewer | You are a code reviewer. Give structured feedback on correctness, security, and performance. |
| Supervisor | Supervisor | You are a task planning supervisor. When asked to plan, output only valid JSON. When asked to synthesise, output a single coherent response. |

Team names must match `studioTeam` in agent registry JSONs exactly.

---

### Step 2: Verify agent registry

Check `agent-registry/agents/` — all five entries must exist:

```
java-dev.json      → studioTeam: "Java Developer Team"
python-dev.json    → studioTeam: "Python Developer Team"
general.json       → studioTeam: "General Team"
reviewer.json      → studioTeam: "Reviewer Team"
supervisor.json    → studioTeam: "Supervisor"
```

---

### Step 3: Verify task registry

Check `agent-registry/tasks/` — three plans provided out of the box:

```
code-review.json       2 steps  SEQUENTIAL  LLM_SUMMARY
feature-build.json     3 steps  SEQUENTIAL  CONCAT
parallel-analysis.json 3 steps  PARALLEL    LLM_SUMMARY
```

To add a new task type: create a new JSON file. No code change needed.

---

### Step 4: Start everything

```bash
# Terminal 1
ollama serve

# Terminal 2
autogenstudio serve --port 8080

# Terminal 3
cd api-gateway && ./mvnw spring-boot:run
# Watch for: "✓ AutoGen Studio is reachable"
# Watch for: "[supervisor] SupervisorActor started"
# Watch for: "[worker] WorkerActor started"
```

---

### Step 5: Smoke tests

```bash
# 1. Health
curl http://localhost:8081/actuator/health

# 2. List agents
curl http://localhost:8081/api/agents

# 3. List task types
curl http://localhost:8081/api/tasks/types

# 4. Single agent (unchanged)
curl -X POST http://localhost:8081/api/agents/java-dev/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "hello world in java"}'

# 5. Multi-agent task — config plan
curl -X POST http://localhost:8081/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"taskType": "code-review", "input": "public void save(User u){db.save(u);}"}'

# 6. Multi-agent task — LLM planner (unknown type)
curl -X POST http://localhost:8081/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"taskType": "custom-analysis", "input": "analyse this spring boot app for bottlenecks"}'

# 7. SSE stream
curl -N -X POST http://localhost:8081/api/tasks/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"taskType": "feature-build", "input": "add JWT auth to the user service"}'
```

---

### Phase 1 Checklist

- [ ] All 5 Studio teams created and named correctly
- [ ] All 5 agent registry entries present
- [ ] All 3 task plan files present
- [ ] Gateway logs show SupervisorActor and WorkerActor started
- [ ] Single-agent invoke still works
- [ ] `code-review` task runs both agents in sequence
- [ ] `feature-build` task passes context from planner → coder → test writer
- [ ] `parallel-analysis` fires all 3 agents simultaneously
- [ ] Unknown task type triggers LLM planner (check gateway logs)
- [ ] SSE stream emits one event per completed step
- [ ] CLI `task` and `task:stream` commands work end-to-end

---

## Phase 2 — Persistence + Redis Bus

- Replace `ReactorMessageBus` with `RedisMessageBus` — no actor changes
- Persist `taskResults` to Redis hash for task recovery across restarts
- Add `GET /api/tasks/{taskId}` to poll task status
- Request/response logging to SQLite
- Registry CRUD API (`POST /api/agents`, `POST /api/tasks/types`)

## Phase 3 — Peer Messaging + Tools

- Agent-to-agent direct messages (`recipientId` = target agentId)
- Dynamic team composition: supervisor creates ad-hoc agent sets per task
- Tool execution via Studio tool definitions
- Multi-turn session memory via Studio session IDs

## Phase 4 — UI + Distribution

- React task dashboard with live agent graph visualisation
- Task history, step replay
- Multi-user with API key auth
- Agent marketplace (import/export registry entries + task plans)
