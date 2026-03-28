# Autonomous AI Agents Team - Setup & Run

This directory contains the configuration and launcher for a team of autonomous AI agents that will build the StreamWeave Platform based on the provided documentation.

## Prerequisites

1. **Ollama**: Install [Ollama](https://ollama.ai/) and pull a coding-optimized model.
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
2. **Python 3.10+**: Ensure you have Python installed.
3. **Dependencies**: Install the required Python packages.
   ```bash
   pip install -r requirements.txt
   ```

## Setup

The team consists of:
- **DocReader**: Analyzes `docs/` to extract requirements.
- **Planner**: Creates the roadmap and task iterations.
- **Architect**: Designs the system according to the blueprint.
- **Developer**: Writes the code for each iteration.
- **Reviewer**: Performs code reviews.
- **UserProxy**: Handles code execution and file saving to `build_output/`.

## Running the Autonomous Team

To launch the team and start the project build:

```bash
python launcher.py
```

The agents will collaborate in a group chat. You can watch the progress in your terminal. The produced code and artifacts will be saved in the `autonomous-team/build_output/` directory.

## Customization

You can modify the `model` name in `launcher.py` to use any other model you have pulled in Ollama.
