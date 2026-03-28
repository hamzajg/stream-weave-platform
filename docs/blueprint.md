# System Blueprint

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    VERTICAL 2 — Clients                           │
│    CLI  │  Aider  │  Web  │  Mobile  │  Bot                      │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼─────────────────────────────────────┐
│                 VERTICAL 1 — Local AI Platform                    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  API Gateway :8081  (Spring Boot)                        │   │
│  │  POST /api/agents/{id}/invoke  (single agent)            │   │
│  │  POST /api/tasks               (multi-agent, blocking)   │   │
│  │  POST /api/tasks/stream        (multi-agent, SSE)        │   │
│  └───────┬──────────────────────────┬───────────────────────┘   │
│          │ single agent             │ multi-agent task           │
│          │                          ▼                            │
│          │      ┌─────────────────────────────────────┐         │
│          │      │  Reactive Message Bus               │         │
│          │      │  MessageBus interface               │         │
│          │      │  ReactorMessageBus (Sinks.Many)     │         │
│          │      └────────┬────────────────┬───────────┘         │
│          │               │                │                      │
│          │    ┌──────────▼──────┐  ┌──────▼──────────┐         │
│          │    │ SupervisorActor │  │  WorkerActor     │         │
│          │    │                 │  │  (any agentId)   │         │
│          │    │ - resolve plan  │  │  - invoke Studio │         │
│          │    │ - dispatch steps│  │  - publish result│         │
│          │    │ - aggregate     │  └──────────────────┘         │
│          │    └─────────────────┘                                │
│          │               │                                       │
│          └───────────────┤                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  AutoGen Studio :8080  (control plane)                   │   │
│  │  POST /api/runs  ·  GET /api/agents                      │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Ollama :11434                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────┐  ┌────────────────────────────────┐  │
│  │  Agent Registry      │  │  Task Registry                  │  │
│  │  agents/*.json       │  │  tasks/*.json                   │  │
│  │  id → studioTeam     │  │  taskType → ExecutionPlan       │  │
│  └──────────────────────┘  └────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Message Bus — Interface and Swap Path

```java
// Phase 1 — already wired
@Service ReactorMessageBus implements MessageBus
  → Sinks.Many<AgentMessage> (in-memory, single JVM)

// Phase 2 — zero actor code change required
@Service RedisMessageBus implements MessageBus
  → RedisTemplate pub/sub (persistent, multi-node)
```

The `MessageBus` interface exposes four methods:
- `publish(AgentMessage)` → `Mono<Void>`
- `subscribe(Class<T>, recipientId)` → `Flux<T>`
- `subscribeAll(Class<T>)` → `Flux<T>`
- `subscribeForTask(Class<T>, taskId)` → `Flux<T>`

---

## 3. Message Hierarchy (Sealed)

```
AgentMessage  (abstract sealed)
├── TaskMessage           gateway → supervisor
├── AgentTaskMessage      supervisor → worker
├── AgentResultMessage    worker → supervisor
├── TaskResultMessage     supervisor → gateway
└── ErrorMessage          any → supervisor
```

Every message carries: `messageId`, `taskId`, `senderId`, `recipientId`, `timestamp`.  
`taskId` links all messages in a single task lifecycle — used for per-task subscriptions.

---

## 4. Supervisor Decision Flow

```
TaskMessage(taskType, input)
    │
    ▼
TaskRegistryService.findByType(taskType)
    │
  found ──────────────────────────────→ TaskPlan (source="config")
    │ not found
    ▼
TaskPlannerService.plan(taskType, input)
    → calls AutoGen Studio Supervisor team
    → parses JSON { steps[], aggregationStrategy }
    → on parse failure: single-agent fallback (general)
    │
    ▼ TaskPlan (source="llm" | "fallback")
    │
    ▼
Execute steps
    ├── SEQUENTIAL: concatMap, each step gets prior {context}
    └── PARALLEL:   Mono.when(), steps fire simultaneously
    │
    ▼
Aggregate
    ├── LAST:        return final step output
    ├── CONCAT:      join all outputs with \n\n
    └── LLM_SUMMARY: Supervisor LLM synthesises all outputs
    │
    ▼
TaskResultMessage → bus → gateway → client
```

---

## 5. Task Plan Config Schema

`agent-registry/tasks/<taskType>.json`

```json
{
  "taskType": "code-review",
  "aggregationStrategy": "LLM_SUMMARY",
  "steps": [
    {
      "agentId": "java-dev",
      "promptTemplate": "Review this code:\n{input}",
      "mode": "SEQUENTIAL"
    },
    {
      "agentId": "reviewer",
      "promptTemplate": "Prior review:\n{context}\n\nNow give security feedback on:\n{input}",
      "mode": "SEQUENTIAL"
    }
  ]
}
```

Prompt templates support two variables:
- `{input}` — the original user prompt
- `{context}` — accumulated output from all prior sequential steps

---

## 6. SSE Stream Event Format

```
POST /api/tasks/stream

data: {"event":"step","agentId":"java-dev","step":1,"output":"..."}
data: {"event":"step","agentId":"reviewer","step":2,"output":"..."}
data: {"event":"done","taskId":"abc-123","output":"...final..."}

-- or on failure --

data: {"event":"error","taskId":"abc-123","message":"Agent timeout"}
```

---

## 7. AutoGen Studio Teams Required

| Team name (in Studio UI) | Used by |
|--------------------------|---------|
| Java Developer Team | `java-dev` agent |
| Python Developer Team | `python-dev` agent |
| General Team | `general` agent |
| Reviewer Team | `reviewer` agent |
| Supervisor | supervisor agent, LLM planner, LLM_SUMMARY aggregation |

Team names must exactly match `studioTeam` in each agent's registry JSON.

---

## 8. Port Map

| Service | Port |
|---------|------|
| AutoGen Studio | 8080 |
| API Gateway | 8081 |
| Ollama | 11434 |

---

## 9. Extension Points

| Future need | How to extend |
|-------------|--------------|
| New agent | Add `agent-registry/agents/<id>.json` + create team in Studio UI |
| New task type | Add `agent-registry/tasks/<type>.json` — no code change |
| Peer-to-peer agent messaging | Worker publishes to specific `recipientId`; target worker subscribes |
| Redis bus | Implement `RedisMessageBus implements MessageBus`, swap Spring bean |
| Tool execution | Define tools in Studio team config — gateway orchestration unchanged |
| Task persistence | Persist `taskResults` map to Redis hash before clearing |
| Dynamic team composition | Supervisor LLM plan references agents not in registry → Studio fallback |
