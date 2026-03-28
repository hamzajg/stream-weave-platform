# StreamWeave Platform — Agent Execution Platform

> A self-hosted, local alternative to the OpenAI API — powered by your own models, agents, and orchestration.

---

## Overview

This platform exposes AutoGen Studio agents via a stable, client-facing REST API. Clients (CLI, Aider, web apps) call **agents by ID** — the platform handles model routing, prompt engineering, and orchestration.

```
Client (CLI / Aider / Web / Mobile)
        │
        │  HTTP / SSE
        ▼
API Gateway :8081          (Spring Boot — stable public surface)
        │
        │  POST /api/runs   (internal)
        ▼
AutoGen Studio :8080        (UI + REST API — control plane)
        │
        ▼
Ollama :11434               (local model runtime)
```

---

## Two Verticals

| Vertical | Role | Components |
|----------|------|------------|
| **Local AI Platform** | Control plane — agent definitions, orchestration, model execution | AutoGen Studio, Ollama, Agent Registry |
| **Client Integration** | Data plane — consume agents via stable API | CLI, Aider, Web / Mobile / Desktop |

---

## Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Control plane | AutoGen Studio (`autogenstudio serve`) | Built-in UI, agent/team builder, REST API, session management — no custom runtime needed |
| API gateway | Spring Boot :8081 | Stable public surface, SSE streaming, agent ID resolution |
| Agent lookup | Registry-first, Studio fallback | Registry owns the ID→Studio-name mapping; Studio API used when registry misses |
| Model provider | Ollama | Local, fast, multi-model |
| Agent storage | JSON registry + AutoGen Studio SQLite | Registry maps IDs; Studio owns agent/team configs |
| Streaming | SSE (Server-Sent Events) | Browser-compatible, mirrors Ollama streaming |
| Custom Python runtime | **Removed** | AutoGen Studio's `serve` replaces it entirely |

---

## Repository Structure
**Solution name:** StreamWeave Platform  
**Repo/project name:** `stream-weave-platform`

```
/stream-weave-platform
 ├── api-gateway/              # Spring Boot — public API, agent resolution, Studio bridge
 │   └── src/main/java/com/localai/gateway/
 │       ├── controller/       # AgentController
 │       ├── service/          # AgentRegistryService, StudioClient, AgentResolverService
 │       ├── model/            # AgentRef, InvokeRequest, InvokeResponse, StudioRun
 │       └── config/           # WebClientConfig
 ├── agent-registry/
 │   └── agents/              # JSON: maps agent IDs → AutoGen Studio team names
 ├── cli/                     # Shell wrapper: ai <agentId> "<prompt>"
 └── docs/
     ├── topdown.md
     ├── blueprint.md
     └── mvp.md
```

> `agent-runtime/` has been **removed**. AutoGen Studio's built-in REST API replaces it.

---

## Quick Start

### 1. Start Ollama
```bash
ollama serve
ollama pull qwen3:4b
```

### 2. Start AutoGen Studio
```bash
pip install autogenstudio
autogenstudio serve --port 8080
# Open http://localhost:8080 — define your agents and teams in the UI
```

### 3. Start API Gateway
```bash
cd api-gateway
./mvnw spring-boot:run
```

### 4. Invoke an agent
```bash
curl -X POST http://localhost:8081/api/agents/java-dev/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "java Hello World!"}'

# or
./cli/ai java-dev "create a Spring Boot REST controller"
```

---

## Agent Resolution — Registry-first, Studio fallback

For `POST /api/agents/java-dev/invoke`:

1. **Registry lookup** — reads `agent-registry/agents/java-dev.json` for `studioTeam`
2. **Studio fallback** — calls `GET http://localhost:8080/api/agents`, matches by name
3. **404** if neither resolves

Registry entry:
```json
{
  "id": "java-dev",
  "studioTeam": "Java Developer Team",
  "description": "Senior Java developer — outputs code only"
}
```

---

## API Reference

### `POST /api/agents/{agentId}/invoke`
```json
{ "input": "java Hello World!", "options": { "stream": false } }
```
```json
{
  "output": "public class HelloWorld { ... }",
  "meta": { "agentId": "java-dev", "studioTeam": "Java Developer Team" }
}
```

Streaming (`"stream": true`) → SSE:
```
data: {"delta": "public class"}
data: {"delta": " HelloWorld"}
data: {"done": true}
```

### `GET /api/agents` — list registered agents
### `GET /api/agents/{agentId}` — get agent metadata

---

## Port Map

| Service | Port |
|---------|------|
| AutoGen Studio (UI + API) | 8080 |
| API Gateway (Spring Boot) | 8081 |
| Ollama | 11434 |

---

## Roadmap

| Phase | Scope |
|-------|-------|
| Phase 1 | Gateway → Studio bridge, registry-first resolution, CLI |
| Phase 2 | SSE streaming, request logs, registry CRUD API |
| Phase 3 | Multi-agent teams via Studio, tool execution, session memory |
| Phase 4 | React UI, agent marketplace, multi-user auth |

---

## Philosophy

> Agents are configuration, not code.  
> Clients never talk to Ollama or AutoGen Studio directly.  
> The gateway is the only public surface.
