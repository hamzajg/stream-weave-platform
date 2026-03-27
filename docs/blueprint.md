# Blueprint

## Components

### API Gateway
- Expose /api/agents/{id}/invoke
- Handle streaming

### Agent Runtime
- Execute AutoGen agents
- Load configurations

### Agent Registry
- Store agent definitions

### Ollama
- Model execution

## Flow
Client -> API -> Runtime -> Ollama -> Response
