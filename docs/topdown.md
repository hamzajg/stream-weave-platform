# Top-Down Problem Solving

## 1. Root Problem

Developers and automation tools need to call AI capabilities without being coupled to specific models, providers, or prompt engineering details.

Currently, every client must know:
- Which model to call
- How to format the prompt
- What system message to use
- How to parse the response

This is **model-coupling** — it breaks every client when the model changes.

---

## 2. Desired State

A client should only need to know:

```
WHO to call (agent ID) + WHAT to ask (input)
```

Everything else — model, system prompt, tools, team topology, temperature — is the platform's concern.

---

## 3. Problem Decomposition

```
Root Problem: Clients are coupled to models
│
├── Problem A: No stable API surface for clients
│   └── Solution: Spring Boot API Gateway :8081
│       POST /api/agents/{id}/invoke
│
├── Problem B: Need an agent execution engine (orchestration)
│   └── Solution: AutoGen Studio (autogenstudio serve :8080)
│       - Built-in UI for defining agents and teams
│       - Built-in REST API: /api/runs, /api/sessions, /api/agents
│       - No custom Python runtime needed
│
├── Problem C: Agent ID → AutoGen Studio team name mapping
│   └── Solution: Registry-first, Studio fallback
│       - Registry (JSON): owns the ID→studioTeam mapping
│       - Studio API: fallback, match by agent name dynamically
│
├── Problem D: Streaming not standardized
│   └── Solution: SSE output from gateway
│       Gateway proxies Studio streaming → SSE to client
│
└── Problem E: No CLI ergonomics
    └── Solution: Shell wrapper
        ai <agentId> "<prompt>"
```

---

## 4. Why AutoGen Studio Replaces the Custom Runtime

The custom Python FastAPI service (`agent-runtime/`) that:
- Wrapped AutoGen agent instantiation
- Called Ollama directly
- Had to be maintained alongside the gateway

AutoGen Studio's `autogenstudio serve` provides all of this out of the box:

| Capability | Before (custom runtime) | Now (AutoGen Studio) |
|-----------|------------------------|----------------------|
| Agent execution | Hand-rolled Python | Studio REST API |
| Agent definitions | JSON + code | Studio UI (visual) |
| Multi-agent teams | DIY | Studio team builder |
| Session management | Not implemented | Studio built-in |
| API surface | FastAPI /run-agent | Studio /api/runs |

The custom runtime is eliminated entirely. The gateway now bridges to Studio's API.

---

## 5. Constraints

| Constraint | Impact |
|-----------|--------|
| Fully local (no cloud) | Ollama only, no external API keys |
| Single developer machine | Docker Compose is max infra complexity |
| Java familiarity | API gateway in Spring Boot |
| MVP speed | JSON registry for Phase 1, no DB overhead |
| AutoGen Studio availability | Must be running before gateway starts |

---

## 6. Key Risks

| Risk | Mitigation |
|------|-----------|
| AutoGen Studio API changes between versions | Pin `autogenstudio` version in requirements |
| Studio not running when gateway starts | Gateway health check polls Studio on startup |
| Agent name mismatch (registry vs Studio) | Fallback to Studio API list; log warnings on mismatch |
| Studio streaming format changes | Isolate Studio client behind an interface — swap without touching gateway |
| Registry and Studio out of sync | Registry is the source of truth for IDs; Studio is the source of truth for execution |

---

## 7. Agent Resolution Flow

```
Gateway receives: POST /api/agents/java-dev/invoke

Step 1 — Registry lookup
  Read agent-registry/agents/java-dev.json
  Found? → use studioTeam: "Java Developer Team"
  Not found? → Step 2

Step 2 — Studio fallback
  GET http://localhost:8080/api/agents
  Find agent where name matches "java-dev" (case-insensitive)
  Found? → use that agent's team/id
  Not found? → 404 to client
```

---

## 8. Success Criteria (MVP)

- [ ] `POST /api/agents/{id}/invoke` triggers a real AutoGen Studio run
- [ ] Registry-first resolution works for known agents
- [ ] Studio fallback resolves unknown agents by name
- [ ] CLI wrapper works end-to-end
- [ ] No client sends requests to Ollama or AutoGen Studio directly
- [ ] Gateway returns 404 with a clear message for unresolvable agents

---

## 9. Non-Goals (Phase 1)

- Authentication / API keys
- Multi-user support
- Persistent conversation memory
- Tool execution (file, web, code)
- Web UI
- Custom Python code in agents (Studio UI only)
