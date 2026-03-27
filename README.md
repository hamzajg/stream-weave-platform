# StreamWeave Platform

## Overview
StreamWeave Platform provides a local enterprise-grade LLM platform that abstracts model execution (Ollama) behind agent-based APIs.

## Architecture
- API Gateway (Spring Boot / FastAPI)
- Agent Runtime (Python + AutoGen)
- Ollama (LLM provider)
- Agent Registry (JSON/DB)

## Key Decisions
- Agents as configuration, not code
- API-first design
- Separation between control plane and data plane
- Streaming-first support
- Model abstraction (Ollama hidden behind API)
