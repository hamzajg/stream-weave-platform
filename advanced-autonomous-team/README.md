# StreamWeave Advanced Autonomous Mesh

This directory contains a professional-grade autonomous agent team designed to build the StreamWeave Platform. It uses a **Hierarchical Actor Mesh** pattern where specialized agents collaborate to analyze, plan, architect, and implement the solution.

## 🏗️ The Agent Team

- **Product Manager (PM)**: The orchestrator who decomposes the roadmap and manages the task lifecycle.
- **System Architect**: Designs the reactive system architecture and component interactions.
- **Lead Developer**: Implements the code based on architectural blueprints.
- **Code Reviewer**: Audits the code for security, performance, and design alignment.
- **User Proxy**: Handles local file persistence and execution.

## 🛠️ Prerequisites

1. **Ollama**: Install [Ollama](https://ollama.ai/) and pull a coding-optimized model.
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
2. **Python 3.10+**: Ensure you have a modern Python environment.
3. **Dependencies**: Install the mesh requirements.
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Launching the Mesh

To start the autonomous build process:

```bash
python launcher.py
```

## 📂 Architecture

- `launcher.py`: The main orchestration engine using AutoGen's `GroupChat`.
- `workspace/`: This is where the agents will build the project. The Lead Developer will save files here.
- `agents/`: (Optional) Extended configurations for individual agents.
- `tools/`: (Optional) Custom Python tools for the agents to use.

## 🧠 Features

- **Context-Aware**: Agents automatically read all documentation in `../docs` before starting.
- **Stateful**: The PM maintains the state of the project build across rounds.
- **Architectural Integrity**: The Architect ensures the Developer follows the specific patterns (Actor Model, Reactor Bus) defined in the blueprint.
- **Local & Private**: All processing happens on your local machine via Ollama.
