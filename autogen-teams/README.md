# AutoGen Studio Team Configurations

This directory contains the team configurations for the autonomous AI agents system. These files need to be imported into AutoGen Studio before running the autonomous workflows.

## 📋 Teams Overview

### 1. Product Manager Team
- **File:** `product-manager-team.json`
- **Purpose:** Analyzes requirements and defines product features
- **Model:** qwen2.5:7b
- **Expertise:** Business analysis, user stories, feature prioritization

### 2. Solution Architect Team
- **File:** `solution-architect-team.json`
- **Purpose:** Designs system architecture and technical solutions
- **Model:** codellama:7b
- **Expertise:** System design, technology selection, API design

### 3. Planning Manager Team
- **File:** `planning-manager-team.json`
- **Purpose:** Decomposes features and creates development plans
- **Model:** qwen2.5:7b
- **Expertise:** Agile planning, task decomposition, effort estimation

### 4. Team Lead Team
- **File:** `team-lead-team.json`
- **Purpose:** Coordinates development teams and assigns tasks
- **Model:** llama3.1:8b
- **Expertise:** Team coordination, resource allocation, quality gates

### 5. Quality Assurance Team
- **File:** `quality-assurance-team.json`
- **Purpose:** Reviews code quality and creates testing strategies
- **Model:** codellama:7b
- **Expertise:** Code review, testing strategy, compliance checking

### 6. Supervisor Team
- **File:** `supervisor-team.json`
- **Purpose:** Coordinates workflows and synthesizes results
- **Model:** qwen2.5:7b
- **Expertise:** Workflow orchestration, result synthesis

## 🔧 Import Instructions

### Method 1: AutoGen Studio UI
1. Start AutoGen Studio: `autogenstudio serve --port 8080`
2. Open http://localhost:8080 in your browser
3. Navigate to "Teams" section
4. Click "Import Team" for each JSON file in this directory
5. Ensure team names match exactly (case-sensitive)

### Method 2: API Import (Advanced)
```bash
# Import all teams via API
for file in *.json; do
    curl -X POST http://localhost:8080/api/teams \
        -H "Content-Type: application/json" \
        -d @"$file"
done
```

## ⚠️ Important Notes

### Team Names Must Match Exactly
The team names in AutoGen Studio must exactly match the `studioTeam` values in the agent registry files:

- `Product Manager Team` ← agent-registry/agents/product-manager.json
- `Solution Architect Team` ← agent-registry/agents/solution-architect.json  
- `Planning Manager Team` ← agent-registry/agents/planning-manager.json
- `Team Lead Team` ← agent-registry/agents/team-lead.json
- `Quality Assurance Team` ← agent-registry/agents/quality-assurance.json
- `Supervisor` ← agent-registry/agents/supervisor.json

### Model Requirements
Ensure these Ollama models are pulled before starting:
```bash
ollama pull qwen2.5:7b    # Product Manager, Planning Manager, Supervisor
ollama pull llama3.1:8b   # Team Lead
ollama pull codellama:7b  # Solution Architect, Quality Assurance
```

### Verification
After importing, verify teams are correctly configured:
```bash
# List all teams
curl http://localhost:8080/api/teams

# Check specific team
curl http://localhost:8080/api/teams/Product%20Manager%20Team
```

## 🔄 Customization

### Modifying Agent Prompts
Edit the `system_message` field in each JSON file to customize agent behavior for your specific domain or requirements.

### Changing Models
Update the `model` field to use different Ollama models based on your preferences and hardware capabilities.

### Adding New Teams
1. Create a new JSON file following the same format
2. Import it into AutoGen Studio
3. Update agent registry and task configurations to reference the new team

## 🐛 Troubleshooting

### Team Not Found Errors
If you get "team not found" errors:
1. Check exact team name spelling and capitalization
2. Verify the team was successfully imported
3. Restart AutoGen Studio and re-import if needed

### Model Not Available
If models are not responding:
1. Run `ollama list` to verify models are downloaded
2. Pull missing models: `ollama pull <model-name>`
3. Restart Ollama service: `pkill ollama && ollama serve`

### Agent Performance Issues
If agents are slow or unresponsive:
1. Try smaller models (qwen2.5:4b instead of 7b)
2. Check system resources (RAM, CPU)
3. Consider GPU acceleration for Ollama

## 📚 Additional Resources

- [AutoGen Studio Documentation](https://microsoft.github.io/autogen/docs/topics/autogen_studio)
- [Ollama Model Library](https://ollama.ai/library)
- [StreamWeave Platform Architecture](../docs/blueprint.md)
