# StreamWeave Platform — Agent Execution Platform

> A self-hosted, local alternative to the OpenAI API — powered by your own models, agents, and orchestration.

---

## Overview

This platform sits between your local AI models (Ollama) and any client integration (CLI, Aider, web apps) by exposing a stable, agent-centric REST API.

Instead of calling models directly, clients call **agents** — which carry identity, configuration, system prompts, tools, and model bindings.

```
Client (CLI / Aider / UI)
        ↓
Agent Gateway  →  POST /api/agents/{id}/invoke
        ↓
AutoGen Studio (Serve / API)
        ↓
Ollama  (local model provider)
```

---

## Two Verticals

| Vertical | Role | Components |
|----------|------|------------|
| **Local AI Platform** | Control plane — model execution, agent orchestration | Ollama, AutoGen Studio |
| **Client Integration** | Data plane — consume agents via stable API | CLI, Aider, Web/Mobile/Desktop |

---

## Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| API layer | Spring Boot | Stable HTTP, easy routing, streaming support |
| Agent runtime + UI | AutoGen Studio | Manage agents/models/tools in UI; serve workflows via HTTP |
| Model provider | Ollama | Local, fast, multi-model |
| Agent storage | AutoGen Studio DB | Studio persists agents/workflows (SQLite by default; configurable) |
| Streaming | SSE (Server-Sent Events) | Mirrors Ollama, browser-compatible |
| Gateway↔Studio | HTTP (internal) | Simple, debuggable, compatible with Studio serve API |
| Agent identity | Config-driven, not code | Agents are data — swappable without redeploy |

---

## Repository Structure

**Solution name:** StreamWeave Platform  
**Repo/project name:** `stream-weave-platform`

```
/stream-weave-platform
 ├── api-gateway/          # Spring Boot — public API surface
 ├── agent-studio/         # Autogen Studio
 ├── cli/                  # Shell wrapper for terminal usage
 └── docs/
     ├── topdown.md        # Problem framing and decomposition
     ├── blueprint.md      # Full system architecture
     └── mvp.md            # Phased startup plan
```

---

## Quick Start (MVP)

### 1. Start Ollama

```bash
ollama serve
ollama pull qwen3:4b
```

### 2. Start AutoGen Studio

```bash
# Start Studio UI (manage agents, models, tools)
autogenstudio ui --host 127.0.0.1 --port 8082

# In a separate terminal: serve a workflow/team as an API
# (port is configurable; see Studio docs)
autogenstudio serve --team path/to/team.json --host 127.0.0.1 --port 8084
```

### 3. Start API Gateway

```bash
cd api-gateway
./mvnw spring-boot:run
# Listens on :8081
```

### 4. Invoke an agent via CLI

```bash
curl http://localhost:8081/api/agents/java-dev/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "java Hello World!"}'
```

Or use the CLI wrapper:

```bash
./cli/ai java-dev "create a Spring Boot REST controller"
```

---

## API Reference

### `POST /api/agents/{agentId}/invoke`

**Request**

```json
{
  "input": "java Hello World!",
  "context": {
    "system": "You are a senior Java developer. Only output code."
  },
  "options": {
    "stream": false,
    "temperature": 0.2
  }
}
```

**Response**

```json
{
  "output": "public class HelloWorld { ... }",
  "usage": { "tokens": 120 },
  "meta": { "agentId": "java-dev", "model": "qwen3:4b" }
}
```

**Streaming** (`"stream": true`) returns SSE:

```
data: {"delta": "public class"}
data: {"delta": " HelloWorld"}
data: {"done": true}
```

---

## Agent Definition Source of Truth

Agents, models, and tools are managed in **AutoGen Studio** (UI + DB). The gateway resolves agent/workflow IDs against Studio (or an exported team/workflow file served by Studio) rather than loading JSON from this repo.

---

## Roadmap


| Phase   | Scope                                                        |
| ------- | ------------------------------------------------------------ |
| Phase 1 | API wrapper + AutoGen Studio integration + CLI               |
| Phase 2 | Streaming, request logs, workflow/agent discovery via Studio |
| Phase 3 | Multi-agent workflows + tools (Studio-managed), memory       |
| Phase 4 | React UI, agent marketplace, multi-user                      |


---

## Philosophy

> Agents are configuration, not code.  
> The platform is the abstraction. Clients never talk to Ollama directly.

