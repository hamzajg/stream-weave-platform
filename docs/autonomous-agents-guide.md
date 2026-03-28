# Autonomous AI Agents Setup Guide

## Overview

This guide walks you through setting up a complete local autonomous AI agents system that can read documentation, plan features, architect solutions, decompose iterations, assign tasks to development teams, and review produced code.

The system is built on the StreamWeave Platform and uses:
- **Ollama** for local LLM inference
- **AutoGen Studio** for agent management and execution
- **Spring Boot API Gateway** for orchestration and coordination

---

## 🚀 Quick Start

### Prerequisites

Ensure you have the following installed:
- **Docker** (recommended) or native installations
- **Python 3.8+** with pip
- **Java 17+** with Maven
- **Node.js 16+** (for UI components)
- **curl** for API testing

### One-Command Setup

```bash
# Clone and setup
git clone <repository-url>
cd stream-weave-platform
./setup/autonomous-agents-setup.sh
```

### Launch the System

```bash
# Start all services
./launch-autonomous-agents.sh

# Or use the CLI helper
./cli/autonomous-ai status
```

---

## 🏗️ System Architecture

### Agent Roles

| Agent | Responsibility | Skills |
|-------|----------------|--------|
| **Product Manager** | Requirements analysis, feature definition | Document analysis, user stories, acceptance criteria |
| **Solution Architect** | System design, technology selection | Architecture diagrams, API design, security |
| **Planning Manager** | Task decomposition, roadmap creation | Iteration planning, effort estimation, dependency mapping |
| **Team Lead** | Task assignment, team coordination | Resource allocation, progress monitoring, quality gates |
| **Quality Assurance** | Code review, testing strategy | Quality metrics, security review, compliance checking |

### Workflow Pipeline

```
User Request → Product Manager → Solution Architect → Planning Manager → Team Lead → Quality Assurance → Final Output
```

---

## 📋 Step-by-Step Setup

### 1. Install Ollama and Models

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull required models
ollama pull qwen2.5:7b      # General reasoning and planning
ollama pull llama3.1:8b     # Complex coordination tasks  
ollama pull codellama:7b    # Technical design and code review
```

### 2. Setup AutoGen Studio

```bash
# Install AutoGen Studio
pip install autogenstudio

# Start AutoGen Studio
autogenstudio serve --port 8080
```

Open http://localhost:8080 and import the team configurations from `autogen-teams/` directory.

### 3. Configure Agent Teams

In AutoGen Studio UI, create these teams with exact names:

1. **Product Manager Team**
   - Agent: Product Manager
   - Model: qwen2.5:7b
   - System Message: Senior product management expertise

2. **Solution Architect Team**
   - Agent: Solution Architect  
   - Model: codellama:7b
   - System Message: Senior architecture expertise

3. **Planning Manager Team**
   - Agent: Planning Manager
   - Model: qwen2.5:7b
   - System Message: Agile planning and decomposition expertise

4. **Team Lead Team**
   - Agent: Team Lead
   - Model: llama3.1:8b
   - System Message: Team coordination and leadership expertise

5. **Quality Assurance Team**
   - Agent: Quality Assurance Engineer
   - Model: codellama:7b
   - System Message: Senior QA and code review expertise

6. **Supervisor**
   - Agent: Supervisor
   - Model: qwen2.5:7b
   - System Message: Workflow coordination and synthesis

### 4. Start API Gateway

```bash
cd api-gateway
./mvnw spring-boot:run
```

The gateway will start on http://localhost:8081

---

## 🎯 Usage Examples

### CLI Interface

```bash
# Check system status
./cli/autonomous-ai status

# Build a complete project
./cli/autonomous-ai build "Create a task management system with user authentication, role-based access, and real-time notifications"

# Develop a specific feature
./cli/autonomous-ai feature "Add file upload functionality with drag-and-drop interface and progress tracking"

# Stream execution in real-time
./cli/autonomous-ai stream autonomous-project-build "Build a blog platform with markdown support"

# List available agents and tasks
./cli/autonomous-ai agents
./cli/autonomous-ai tasks
```

### Direct API Usage

```bash
# Autonomous project build
curl -X POST http://localhost:8081/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "taskType": "autonomous-project-build",
    "input": "Build a customer relationship management (CRM) system with contact management, sales pipeline tracking, and reporting dashboard"
  }'

# Feature development cycle
curl -X POST http://localhost:8081/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "taskType": "feature-development-cycle", 
    "input": "Implement two-factor authentication with SMS and email options"
  }'

# Real-time streaming
curl -N -X POST http://localhost:8081/api/tasks/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "taskType": "autonomous-project-build",
    "input": "Create an e-commerce platform with product catalog and shopping cart"
  }'
```

---

## 📊 What the System Produces

### Project Build Output

When you request a complete project build, the system delivers:

1. **Product Requirements**
   - Feature specifications
   - User stories with acceptance criteria
   - Business requirements and success metrics

2. **Technical Architecture**
   - System architecture overview
   - Technology stack recommendations
   - API specifications
   - Database schema design
   - Security architecture

3. **Development Roadmap**
   - Iteration breakdown (2-week sprints)
   - Task dependencies and critical path
   - Effort estimates and timeline
   - Risk assessment

4. **Team Assignment Plan**
   - Task assignments to developer agents
   - Coordination requirements
   - Quality gates and review points

5. **Quality Assurance Strategy**
   - Code review processes
   - Testing strategy (unit, integration, e2e)
   - Quality metrics and compliance checks

### Feature Development Output

For feature requests, you get:
- Detailed feature specifications
- Technical implementation approach
- Task breakdown with estimates
- Developer assignments
- Testing and review requirements

---

## 🔧 Configuration and Customization

### Adding New Agents

1. Create agent registry entry:
```json
// agent-registry/agents/new-agent.json
{
  "agentId": "new-agent",
  "studioTeam": "New Agent Team",
  "description": "Agent description",
  "capabilities": ["capability1", "capability2"]
}
```

2. Create corresponding team in AutoGen Studio

3. Update task plans to include the new agent

### Creating Custom Task Types

```json
// agent-registry/tasks/custom-task.json
{
  "taskType": "custom-task",
  "aggregationStrategy": "LLM_SUMMARY",
  "steps": [
    {
      "agentId": "agent1",
      "promptTemplate": "Process this: {input}",
      "mode": "SEQUENTIAL"
    },
    {
      "agentId": "agent2", 
      "promptTemplate": "Build on previous: {context}\n\nNew input: {input}",
      "mode": "SEQUENTIAL"
    }
  ]
}
```

### Model Configuration

Update agent models in AutoGen Studio UI:
- Use `qwen2.5:7b` for reasoning and planning tasks
- Use `codellama:7b` for technical design and code
- Use `llama3.1:8b` for complex coordination

---

## 🐛 Troubleshooting

### Common Issues

**AutoGen Studio not connecting:**
```bash
# Check if AutoGen Studio is running
curl http://localhost:8080

# Restart if needed
pkill -f autogenstudio
autogenstudio serve --port 8080
```

**Ollama models not responding:**
```bash
# Check Ollama status
ollama list

# Restart Ollama
pkill -f ollama
ollama serve
```

**API Gateway connection issues:**
```bash
# Check gateway health
curl http://localhost:8081/actuator/health

# Check logs
cd api-gateway && tail -f target/spring-boot-app.log
```

**Team name mismatches:**
Ensure AutoGen Studio team names exactly match `studioTeam` values in agent registry JSON files.

### Performance Optimization

- Use smaller models (qwen2.5:7b) for faster response
- Enable parallel execution for independent tasks
- Monitor memory usage on systems with limited RAM
- Consider GPU acceleration for Ollama if available

---

## 🔒 Security Considerations

- All processing happens locally - no data leaves your system
- Ensure firewall rules only expose necessary ports
- Regular updates of Ollama models recommended
- Monitor system resources during long-running tasks

---

## 📈 Monitoring and Scaling

### System Monitoring

```bash
# Check service status
./cli/autonomous-ai status

# Monitor resource usage
htop  # or Activity Monitor on macOS

# View API Gateway logs
cd api-gateway && tail -f logs/spring.log
```

### Scaling Options

- **Phase 2:** Redis message bus for multi-node deployment
- **Phase 3:** Dynamic team composition and peer messaging
- **Phase 4:** Web UI with task visualization

---

## 🎉 Success Examples

### Example 1: E-commerce Platform

```bash
./cli/autonomous-ai build "Build an e-commerce platform with product catalog, user authentication, shopping cart, and payment integration"
```

**Result:** Complete project plan with 6 development iterations, detailed API specs, database schema, and 3-month roadmap.

### Example 2: Feature Addition

```bash
./cli/autonomous-ai feature "Add real-time chat functionality with typing indicators and read receipts"
```

**Result:** Technical design, WebSocket implementation plan, testing strategy, and 2-week development schedule.

---

## 📚 Next Steps

1. **Explore the UI:** Open AutoGen Studio at http://localhost:8080
2. **Try Examples:** Use the CLI commands above
3. **Customize Agents:** Modify agent prompts for your domain
4. **Extend Workflows:** Create custom task types
5. **Monitor Performance:** Track execution times and quality

---

## 🤝 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review service logs for error details
3. Verify team configurations in AutoGen Studio
4. Ensure all prerequisites are properly installed

The autonomous agents system is now ready to transform your ideas into detailed, actionable project plans with minimal human intervention!
