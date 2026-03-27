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
Agent Runtime  (Python / AutoGen)
        ↓
Ollama  (local model provider)
```

---

## Two Verticals

| Vertical | Role | Components |
|----------|------|------------|
| **Local AI Platform** | Control plane — model execution, agent orchestration | Ollama, AutoGen, Agent Registry |
| **Client Integration** | Data plane — consume agents via stable API | CLI, Aider, Web/Mobile/Desktop |

---

## Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| API layer | Spring Boot | Stable HTTP, easy routing, streaming support |
| Agent runtime | Python + FastAPI | AutoGen is Python-native |
| Model provider | Ollama | Local, fast, multi-model |
| Agent storage | JSON / SQLite (Phase 1) | Simple, no overhead for MVP |
| Streaming | SSE (Server-Sent Events) | Mirrors Ollama, browser-compatible |
| Gateway↔Runtime | HTTP (internal) | Simple, debuggable, upgradeable to queue |
| Agent identity | Config-driven, not code | Agents are data — swappable without redeploy |

---

## Repository Structure

**Solution name:** StreamWeave Platform  
**Repo/project name:** `stream-weave-platform`

```
/stream-weave-platform
 ├── api-gateway/          # Spring Boot — public API surface
 ├── agent-runtime/        # Python FastAPI — AutoGen execution engine
 ├── agent-registry/       # Agent config definitions (JSON)
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

### 2. Start Agent Runtime
```bash
cd agent-runtime
pip install -r requirements.txt
uvicorn main:app --port 9000
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

## Agent Config Example

Agents are defined in `agent-registry/agents/`:

```json
{
  "id": "java-dev",
  "model": "qwen3:4b",
  "system": "You are a senior Java developer. Only output code. No explanation.",
  "mode": "code",
  "temperature": 0.2,
  "tools": []
}
```

---

## Roadmap

| Phase | Scope |
|-------|-------|
| Phase 1 | API wrapper, single agent execution, CLI |
| Phase 2 | Streaming, agent registry DB, request logs |
| Phase 3 | Multi-agent workflows (AutoGen), tool execution, memory |
| Phase 4 | React UI, agent marketplace, multi-user |

---

## Philosophy

> Agents are configuration, not code.  
> The platform is the abstraction. Clients never talk to Ollama directly.
