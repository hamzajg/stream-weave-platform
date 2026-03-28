# StreamWeave Platform — Agent Execution Platform

> A self-hosted, local alternative to the OpenAI API — with single-agent invocation and multi-agent task orchestration via the actor model and reactive messaging.

---

## Overview

```
Client (CLI / Aider / Web)
        │
        │  HTTP / SSE
        ▼
API Gateway :8081          Spring Boot — public surface
        │
        ├─ POST /api/agents/{id}/invoke   → single agent (direct)
        └─ POST /api/tasks                → multi-agent task (actor mesh)
                │
                ▼
        Reactive Message Bus              Project Reactor Sinks (swap to Redis in Phase 2)
                │
        ┌───────┴────────┐
        │                │
   SupervisorActor   WorkerActor(s)
        │                │
        └───────┬────────┘
                ▼
        AutoGen Studio :8080              control plane — LLM execution
                │
                ▼
        Ollama :11434                     local model runtime
```

---

## Two Entry Points

| Endpoint | Use case | Pattern |
|----------|----------|---------|
| `POST /api/agents/{id}/invoke` | Single agent, simple prompt → response | Direct Studio call |
| `POST /api/tasks` | Complex task needing multiple agents | Actor model + message bus |
| `POST /api/tasks/stream` | Same, with live SSE step progress | Actor model + SSE |

---

## Multi-Agent Architecture

### Actor model

Every agent is an **actor** — it has a mailbox (bus subscription), processes one message at a time, and communicates only by publishing messages. No shared state, no direct method calls between agents.

### Message types

| Message | Flow | Purpose |
|---------|------|---------|
| `TaskMessage` | gateway → supervisor | Client submits a task |
| `AgentTaskMessage` | supervisor → worker | Assign one step to one agent |
| `AgentResultMessage` | worker → supervisor | Step output published |
| `TaskResultMessage` | supervisor → gateway | Final aggregated result |
| `ErrorMessage` | any → supervisor | Fault signalling |

### Supervisor decision: config-first, LLM fallback

```
TaskMessage arrives (taskType + input)
        │
        ▼
TaskRegistryService.findByType(taskType)
        │
   found? ──yes──→ load JSON plan from agent-registry/tasks/
        │
        no
        │
        ▼
TaskPlannerService.plan(taskType, input)
   → sends planning prompt to Supervisor LLM via Studio
   → parses JSON plan from LLM response
   → falls back to single general agent if parse fails
        │
        ▼
ExecutionPlan resolved → dispatch steps
```

### Execution modes

| Mode | Behaviour |
|------|-----------|
| `SEQUENTIAL` | Each step waits for the prior step's result, which is passed as `{context}` |
| `PARALLEL` | All steps fire simultaneously, results collected with `Mono.when()` |

### Aggregation strategies

| Strategy | Output |
|----------|--------|
| `LAST` | Only the final step's output returned to client |
| `CONCAT` | All step outputs joined in order |
| `LLM_SUMMARY` | Supervisor LLM synthesises all step outputs into one response |

---

## Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Control plane | AutoGen Studio (`autogenstudio serve`) | Built-in UI, agent builder, REST API |
| API gateway | Spring Boot :8081 | Stable surface, SSE, reactive |
| Actor messaging | Project Reactor `Sinks.Many` | Already in stack; swappable to Redis |
| Bus abstraction | `MessageBus` interface | Swap from Reactor → Redis with no actor code change |
| Supervisor planning | Config-first + LLM fallback | Deterministic for known task types; flexible for unknown |
| Execution | Sequential + parallel modes per step | Handles both pipeline and fan-out patterns |
| Aggregation | LAST / CONCAT / LLM_SUMMARY | Covers simple, structured, and synthesised outputs |

---

## Repository Structure
**Solution name:** StreamWeave Platform  
**Repo/project name:** `stream-weave-platform`

```
/stream-weave-platform
 ├── api-gateway/src/main/java/com/localai/gateway/
 │   ├── controller/
 │   │   ├── AgentController.java          single-agent endpoint
 │   │   └── TaskController.java           multi-agent task endpoint
 │   ├── model/
 │   │   ├── message/                      sealed message hierarchy
 │   │   │   ├── AgentMessage.java         base
 │   │   │   ├── TaskMessage.java
 │   │   │   ├── AgentTaskMessage.java
 │   │   │   ├── AgentResultMessage.java
 │   │   │   ├── TaskResultMessage.java
 │   │   │   └── ErrorMessage.java
 │   │   └── task/
 │   │       ├── TaskPlan.java
 │   │       └── TaskPlanStep.java
 │   ├── service/
 │   │   ├── bus/
 │   │   │   ├── MessageBus.java           interface (swap-safe)
 │   │   │   └── ReactorMessageBus.java    Reactor Sinks impl
 │   │   ├── actor/
 │   │   │   ├── SupervisorActor.java      orchestration brain
 │   │   │   └── WorkerActor.java          per-step executor
 │   │   ├── task/
 │   │   │   ├── TaskRegistryService.java  config-first plan lookup
 │   │   │   └── TaskPlannerService.java   LLM fallback planner
 │   │   ├── AgentRegistryService.java
 │   │   ├── AgentResolverService.java
 │   │   └── StudioClient.java
 │   └── config/
 │       ├── WebClientConfig.java
 │       ├── GlobalExceptionHandler.java
 │       └── StudioHealthCheck.java
 ├── agent-registry/
 │   ├── agents/                           agent ID → Studio team mapping
 │   │   ├── java-dev.json
 │   │   ├── python-dev.json
 │   │   ├── general.json
 │   │   ├── reviewer.json
 │   │   └── supervisor.json
 │   └── tasks/                            task type → execution plan
 │       ├── code-review.json
 │       ├── feature-build.json
 │       └── parallel-analysis.json
 ├── cli/ai                                shell wrapper
 └── docs/
     ├── topdown.md
     ├── blueprint.md
     └── mvp.md
```

---

## Quick Start

```bash
# 1. Start Ollama
ollama serve && ollama pull qwen3:4b

# 2. Start AutoGen Studio
autogenstudio serve --port 8080
# Define agents and teams in the UI at http://localhost:8080
# Required teams: Java Developer Team, Python Developer Team,
#                 General Team, Reviewer Team, Supervisor

# 3. Start Gateway
cd api-gateway && ./mvnw spring-boot:run
```

---

## API Examples

```bash
# Single agent
curl -X POST http://localhost:8081/api/agents/java-dev/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "write a REST controller for /users"}'

# Multi-agent task (blocking)
curl -X POST http://localhost:8081/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"taskType": "code-review", "input": "public void save(User u) { db.save(u); }"}'

# Multi-agent task (SSE stream)
curl -N -X POST http://localhost:8081/api/tasks/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"taskType": "feature-build", "input": "add JWT auth to the user service"}'

# Unknown task type → LLM planner kicks in
curl -X POST http://localhost:8081/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"taskType": "anything-custom", "input": "analyse this architecture diagram..."}'
```

## CLI Examples

```bash
./cli/ai agents                                        # list agents
./cli/ai tasks                                         # list task types
./cli/ai java-dev "hello world"                        # single agent
./cli/ai task code-review "review this method..."     # multi-agent task
./cli/ai task:stream feature-build "add OAuth login"  # live stream
```

---

## Port Map

| Service | Port |
|---------|------|
| AutoGen Studio | 8080 |
| API Gateway | 8081 |
| Ollama | 11434 |

---

## Roadmap

| Phase | Scope |
|-------|-------|
| Phase 1 | Single-agent invoke, actor mesh, config+LLM planning, SSE streaming |
| Phase 2 | Redis message bus, task persistence, agent session memory |
| Phase 3 | Peer-to-peer agent messaging, dynamic team composition, tool execution |
| Phase 4 | React UI with live task graph visualisation, multi-user auth |
