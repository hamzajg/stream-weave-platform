# Top-Down Problem Solving

## 1. Root Problem

Complex business tasks cannot be solved by a single AI agent. They require decomposition, specialisation, and synthesis across multiple agents — while remaining transparent, fault-tolerant, and extensible.

---

## 2. Desired State

A client submits a task with a type and a prompt. The platform:
- determines which agents are needed (automatically)
- coordinates their execution (sequentially or in parallel)
- aggregates their outputs
- streams progress back in real time

The client never knows how many agents ran or how they were coordinated.

---

## 3. Problem Decomposition

```
Root Problem: Complex tasks need multiple coordinated agents
│
├── Problem A: How does the platform know which agents to involve?
│   └── Solution: Config-first task registry + LLM fallback planner
│       - Known task types → JSON plan loaded from agent-registry/tasks/
│       - Unknown task types → Supervisor LLM generates a plan on the fly
│
├── Problem B: How do agents communicate without coupling?
│   └── Solution: Actor model + reactive message bus
│       - Agents never call each other directly
│       - All communication is typed messages on the bus
│       - MessageBus interface abstracts Reactor Sinks (now) → Redis (later)
│
├── Problem C: How does the supervisor handle sequential vs parallel steps?
│   └── Solution: TaskPlanStep.Mode (SEQUENTIAL | PARALLEL)
│       - SEQUENTIAL: each step waits for prior output (passed as {context})
│       - PARALLEL: all steps fire together with Mono.when()
│
├── Problem D: How are multi-agent outputs combined?
│   └── Solution: AggregationStrategy per task plan
│       - LAST: return only final step (pipeline pattern)
│       - CONCAT: ordered join of all outputs
│       - LLM_SUMMARY: supervisor synthesises all outputs
│
├── Problem E: How does the client see progress during a long task?
│   └── Solution: POST /api/tasks/stream → SSE
│       - AgentResultMessage events → step SSE events
│       - TaskResultMessage → done SSE event
│
└── Problem F: What happens when an agent fails mid-task?
    └── Solution: ErrorMessage → SupervisorActor short-circuits
        - Publishes TaskResultMessage.failed() immediately
        - Cleans up per-task state
        - Client receives error event on SSE or 500 on blocking call
```

---

## 4. Actor Model Mapping

```
Traditional call-based                Actor model (this platform)
──────────────────────────────────    ──────────────────────────────────────
controller.invokeAgent(agentId)       bus.publish(new AgentTaskMessage(...))
wait for return value                 subscribe to AgentResultMessage for taskId
handle exception inline               ErrorMessage flows to supervisor
tight coupling                        zero coupling — agents don't know each other
hard to add new agents                add agent + subscribe to bus → done
```

---

## 5. Constraints

| Constraint | Impact |
|-----------|--------|
| Fully local | Ollama + AutoGen Studio only |
| Single JVM (Phase 1) | Reactor Sinks is sufficient; Redis for multi-node later |
| AutoGen Studio must run | Gateway health-checks Studio on startup |
| LLM plan parsing can fail | Fallback to single-agent general on any parse error |
| Timeout risk on long tasks | POST /api/tasks has 5-minute timeout; use /stream for long tasks |

---

## 6. Key Risks

| Risk | Mitigation |
|------|-----------|
| LLM generates invalid plan JSON | `extractJson()` strips fences; parse error → single-agent fallback |
| Agent step times out | Per-step Reactor timeout; ErrorMessage triggers task failure |
| Bus backpressure under load | Sinks buffer 1024 messages; overflow logged, emit fails gracefully |
| Task state leaks | `taskResults` map cleared in `doFinally()` and on error handler |
| Studio unavailable mid-task | StudioClient error propagates as ErrorMessage → task fails cleanly |

---

## 7. Success Criteria (Phase 1)

- [ ] `POST /api/tasks` with known taskType runs correct agents in correct order
- [ ] `POST /api/tasks` with unknown taskType triggers LLM planner and runs
- [ ] Sequential steps receive prior output as `{context}` in their prompt
- [ ] Parallel steps all fire simultaneously and results collected correctly
- [ ] `POST /api/tasks/stream` emits one SSE event per completed step
- [ ] Failed step publishes ErrorMessage; supervisor emits failed TaskResultMessage
- [ ] Single-agent `/api/agents/{id}/invoke` still works unchanged

---

## 8. Non-Goals (Phase 1)

- Agent-to-agent peer messaging (Phase 3)
- Dynamic team composition at runtime
- Task persistence across restarts
- Redis-backed bus (interface is ready, impl is Phase 2)
- Tool execution within agent steps
