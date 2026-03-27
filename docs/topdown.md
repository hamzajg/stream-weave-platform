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

Everything else — model, system prompt, tools, temperature — is the platform's concern.

---

## 3. Problem Decomposition

```
Root Problem: Clients are coupled to models
│
├── Problem A: No stable API surface
│   └── Solution: Agent Gateway (Spring Boot)
│
├── Problem B: AutoGen is not HTTP-native
│   └── Solution: Python FastAPI wrapper around AutoGen runtime
│
├── Problem C: No agent identity/registry
│   └── Solution: JSON-based agent config store
│
├── Problem D: Streaming not standardized
│   └── Solution: SSE output from gateway
│
└── Problem E: No CLI ergonomics
    └── Solution: Shell wrapper `ai <agent> "<prompt>"`
```

---

## 4. Constraints

| Constraint | Impact |
|-----------|--------|
| Fully local (no cloud) | Ollama only, no API keys |
| Single developer machine | No Kubernetes, Docker Compose is max |
| Python runtime required | AutoGen is Python — non-negotiable |
| Java familiarity | API gateway in Spring Boot |
| MVP speed | No DB for Phase 1 — JSON files |

---

## 5. Key Risks

| Risk | Mitigation |
|------|-----------|
| AutoGen adds latency | Bypass it for simple single-agent calls |
| Python process crashes | Gateway health-checks runtime on startup |
| Agent config drift | Schema validate on load |
| Streaming complexity | SSE is simpler than WebSocket — use it |

---

## 6. Success Criteria (MVP)

- [ ] `POST /api/agents/{id}/invoke` returns a response
- [ ] At least 2 agents defined (java-dev, general)
- [ ] CLI wrapper works end-to-end
- [ ] System prompt is NOT sent by client — resolved from registry
- [ ] No direct Ollama calls from any client

---

## 7. Non-Goals (Phase 1)

- Authentication / API keys
- Multi-user support
- Persistent memory
- Tool execution
- Web UI
