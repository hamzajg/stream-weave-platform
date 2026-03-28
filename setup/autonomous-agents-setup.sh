#!/bin/bash

# Autonomous AI Agents Setup Script for StreamWeave Platform
# This script sets up the complete autonomous agent development system

set -e

echo "🚀 Setting up Autonomous AI Agents System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Ollama is installed
    if ! command -v ollama &> /dev/null; then
        print_error "Ollama is not installed. Please install it first: https://ollama.ai/"
        exit 1
    fi
    
    # Check if Python is installed (for AutoGen Studio)
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Maven is installed (for API Gateway)
    if ! command -v mvn &> /dev/null; then
        print_error "Maven is not installed. Please install it first."
        exit 1
    fi
    
    print_success "All prerequisites are installed!"
}

# Install and configure Ollama models
setup_ollama() {
    print_status "Setting up Ollama with required models..."
    
    # Start Ollama service
    if ! pgrep -f "ollama serve" > /dev/null; then
        print_status "Starting Ollama service..."
        ollama serve &
        sleep 5
    fi
    
    # Pull required models
    print_status "Pulling required AI models..."
    ollama pull qwen2.5:7b
    ollama pull llama3.1:8b
    ollama pull codellama:7b
    
    print_success "Ollama models are ready!"
}

# Install and setup AutoGen Studio
setup_autogen_studio() {
    print_status "Setting up AutoGen Studio..."
    
    # Install AutoGen Studio if not already installed
    if ! command -v autogenstudio &> /dev/null; then
        print_status "Installing AutoGen Studio..."
        pip install autogenstudio
    fi
    
    print_success "AutoGen Studio is installed!"
}

# Create AutoGen Studio teams configuration
create_autogen_teams() {
    print_status "Creating AutoGen Studio teams configuration..."
    
    # Create teams directory
    mkdir -p autogen-teams
    
    # Create team configurations
    cat > autogen-teams/product-manager-team.json << 'EOF'
{
  "name": "Product Manager Team",
  "description": "Analyzes requirements and defines product features",
  "agents": [
    {
      "name": "Product Manager",
      "system_message": "You are a senior Product Manager with expertise in requirement analysis, user story creation, and feature prioritization. You excel at reading documentation, understanding business needs, and defining comprehensive product specifications. Always provide structured, actionable outputs with clear acceptance criteria.",
      "model": {
        "provider": "ollama",
        "model": "qwen2.5:7b"
      }
    }
  ]
}
EOF

    cat > autogen-teams/solution-architect-team.json << 'EOF'
{
  "name": "Solution Architect Team", 
  "description": "Designs system architecture and technical solutions",
  "agents": [
    {
      "name": "Solution Architect",
      "system_message": "You are a senior Solution Architect with deep expertise in system design, technology selection, and architectural patterns. You specialize in creating scalable, secure, and maintainable system designs. Provide detailed technical specifications, diagrams descriptions, and rationale for architectural decisions.",
      "model": {
        "provider": "ollama",
        "model": "codellama:7b"
      }
    }
  ]
}
EOF

    cat > autogen-teams/planning-manager-team.json << 'EOF'
{
  "name": "Planning Manager Team",
  "description": "Decomposes features and creates development plans",
  "agents": [
    {
      "name": "Planning Manager", 
      "system_message": "You are a senior Planning Manager with expertise in agile methodologies, project planning, and task decomposition. You excel at breaking down complex features into manageable tasks, estimating effort, and creating realistic development roadmaps. Always provide detailed timelines and dependency mappings.",
      "model": {
        "provider": "ollama",
        "model": "qwen2.5:7b"
      }
    }
  ]
}
EOF

    cat > autogen-teams/team-lead-team.json << 'EOF'
{
  "name": "Team Lead Team",
  "description": "Coordinates development teams and assigns tasks",
  "agents": [
    {
      "name": "Team Lead",
      "system_message": "You are an experienced Team Lead with expertise in software development coordination, task assignment, and team management. You excel at optimizing developer workflows, identifying bottlenecks, and ensuring high-quality deliverables. Provide clear task assignments and coordination strategies.",
      "model": {
        "provider": "ollama", 
        "model": "llama3.1:8b"
      }
    }
  ]
}
EOF

    cat > autogen-teams/quality-assurance-team.json << 'EOF'
{
  "name": "Quality Assurance Team",
  "description": "Reviews code quality and creates testing strategies",
  "agents": [
    {
      "name": "Quality Assurance Engineer",
      "system_message": "You are a senior Quality Assurance Engineer with expertise in code review, testing strategies, and quality assurance processes. You excel at identifying potential issues, creating comprehensive test plans, and ensuring compliance with quality standards. Provide detailed review checklists and testing requirements.",
      "model": {
        "provider": "ollama",
        "model": "codellama:7b"
      }
    }
  ]
}
EOF

    cat > autogen-teams/supervisor-team.json << 'EOF'
{
  "name": "Supervisor",
  "description": "Coordinates autonomous agent workflows and synthesizes results",
  "agents": [
    {
      "name": "Supervisor",
      "system_message": "You are a Supervisor agent responsible for coordinating autonomous development workflows. When planning tasks, output only valid JSON with steps array. When synthesizing results, create coherent, comprehensive summaries that integrate all agent outputs effectively.",
      "model": {
        "provider": "ollama",
        "model": "qwen2.5:7b"
      }
    }
  ]
}
EOF

    print_success "AutoGen Studio team configurations created!"
}

# Setup API Gateway
setup_api_gateway() {
    print_status "Setting up API Gateway..."
    
    # Check if we're in the right directory
    if [ ! -f "api-gateway/pom.xml" ]; then
        print_error "API Gateway project not found. Please run this script from the stream-weave-platform root directory."
        exit 1
    fi
    
    # Build the API Gateway
    cd api-gateway
    ./mvnw clean compile
    cd ..
    
    print_success "API Gateway is ready!"
}

# Create launch scripts
create_launch_scripts() {
    print_status "Creating launch scripts..."
    
    # Main launch script
    cat > launch-autonomous-agents.sh << 'EOF'
#!/bin/bash

# Autonomous AI Agents Launch Script

set -e

echo "🚀 Launching Autonomous AI Agents System..."

# Function to check if service is running
check_service() {
    local service=$1
    local port=$2
    if curl -s "http://localhost:$port" > /dev/null; then
        echo "✅ $service is running on port $port"
        return 0
    else
        echo "❌ $service is not running on port $port"
        return 1
    fi
}

# Start Ollama
echo "Starting Ollama..."
if ! pgrep -f "ollama serve" > /dev/null; then
    ollama serve &
    sleep 5
fi

# Start AutoGen Studio
echo "Starting AutoGen Studio..."
if ! check_service "AutoGen Studio" 8080; then
    autogenstudio serve --port 8080 &
    sleep 10
fi

# Start API Gateway
echo "Starting API Gateway..."
if ! check_service "API Gateway" 8081; then
    cd api-gateway
    ./mvnw spring-boot:run &
    cd ..
    sleep 15
fi

# Wait for all services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check all services
echo "Service Status:"
check_service "Ollama" 11434
check_service "AutoGen Studio" 8080
check_service "API Gateway" 8081

echo ""
echo "🎉 Autonomous AI Agents System is ready!"
echo ""
echo "Available endpoints:"
echo "  - API Gateway: http://localhost:8081"
echo "  - AutoGen Studio: http://localhost:8080"
echo "  - Ollama: http://localhost:11434"
echo ""
echo "Example usage:"
echo "  curl -X POST http://localhost:8081/api/tasks \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"taskType\": \"autonomous-project-build\", \"input\": \"Build a task management system with user authentication\"}'"
EOF

    chmod +x launch-autonomous-agents.sh
    
    # Create CLI helper script
    cat > cli/autonomous-ai << 'EOF'
#!/bin/bash

# Autonomous AI CLI Helper

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    echo "Autonomous AI Agents CLI"
    echo ""
    echo "Usage: $0 [command] [args]"
    echo ""
    echo "Commands:"
    echo "  build [project-description]    Start autonomous project build"
    echo "  feature [feature-request]      Start feature development cycle"
    echo "  status                         Check system status"
    echo "  agents                         List available agents"
    echo "  tasks                          List available task types"
    echo "  stream [task-type] [input]     Stream task execution"
    echo "  help                           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 build \"Create a task management app with user auth\""
    echo "  $0 feature \"Add file upload functionality\""
    echo "  $0 stream autonomous-project-build \"Build a blog platform\""
}

check_status() {
    echo -e "${BLUE}Checking Autonomous AI System Status...${NC}"
    echo ""
    
    # Check services
    if curl -s http://localhost:11434 > /dev/null; then
        echo -e "✅ Ollama: ${GREEN}Running${NC}"
    else
        echo -e "❌ Ollama: ${RED}Not running${NC}"
    fi
    
    if curl -s http://localhost:8080 > /dev/null; then
        echo -e "✅ AutoGen Studio: ${GREEN}Running${NC}"
    else
        echo -e "❌ AutoGen Studio: ${RED}Not running${NC}"
    fi
    
    if curl -s http://localhost:8081/actuator/health > /dev/null; then
        echo -e "✅ API Gateway: ${GREEN}Running${NC}"
    else
        echo -e "❌ API Gateway: ${RED}Not running${NC}"
    fi
}

list_agents() {
    echo -e "${BLUE}Available Autonomous Agents:${NC}"
    echo ""
    curl -s http://localhost:8081/api/agents | jq -r '.[] | "  • \(.agentId): \(.description)"' 2>/dev/null || echo "  Error: Could not fetch agents. Is the system running?"
}

list_tasks() {
    echo -e "${BLUE}Available Task Types:${NC}"
    echo ""
    curl -s http://localhost:8081/api/tasks/types | jq -r '.[] | "  • \(.taskType): \(.description)"' 2>/dev/null || echo "  Error: Could not fetch task types. Is the system running?"
}

execute_task() {
    local task_type="$1"
    local input="$2"
    
    if [ -z "$task_type" ] || [ -z "$input" ]; then
        echo "Error: Both task type and input are required."
        echo "Usage: $0 [build|feature] \"description\""
        exit 1
    fi
    
    # Map command to task type
    case "$task_type" in
        "build")
            task_type="autonomous-project-build"
            ;;
        "feature")
            task_type="feature-development-cycle"
            ;;
    esac
    
    echo -e "${BLUE}Executing autonomous task: ${YELLOW}$task_type${NC}"
    echo -e "${BLUE}Input: ${YELLOW}$input${NC}"
    echo ""
    
    curl -X POST http://localhost:8081/api/tasks \
        -H "Content-Type: application/json" \
        -d "{\"taskType\": \"$task_type\", \"input\": \"$input\"}" \
        | jq . 2>/dev/null || echo "Error executing task. Is the system running?"
}

stream_task() {
    local task_type="$1"
    local input="$2"
    
    if [ -z "$task_type" ] || [ -z "$input" ]; then
        echo "Error: Both task type and input are required."
        echo "Usage: $0 stream [task-type] \"description\""
        exit 1
    fi
    
    echo -e "${BLUE}Streaming autonomous task: ${YELLOW}$task_type${NC}"
    echo -e "${BLUE}Input: ${YELLOW}$input${NC}"
    echo ""
    
    curl -N -X POST http://localhost:8081/api/tasks/stream \
        -H "Content-Type: application/json" \
        -H "Accept: text/event-stream" \
        -d "{\"taskType\": \"$task_type\", \"input\": \"$input\"}"
}

# Command routing
case "$1" in
    "build")
        execute_task "build" "$2"
        ;;
    "feature")
        execute_task "feature" "$2"
        ;;
    "stream")
        stream_task "$2" "$3"
        ;;
    "status")
        check_status
        ;;
    "agents")
        list_agents
        ;;
    "tasks")
        list_tasks
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
EOF

    chmod +x cli/autonomous-ai
    
    print_success "Launch scripts created!"
}

# Main execution
main() {
    print_status "Starting Autonomous AI Agents setup..."
    
    check_prerequisites
    setup_ollama
    setup_autogen_studio
    create_autogen_teams
    setup_api_gateway
    create_launch_scripts
    
    print_success "🎉 Autonomous AI Agents setup complete!"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Run: ./launch-autonomous-agents.sh"
    echo "2. Open AutoGen Studio: http://localhost:8080"
    echo "3. Import team configurations from autogen-teams/ directory"
    echo "4. Use the CLI: ./cli/autonomous-ai build \"your project idea\""
    echo ""
    echo -e "${YELLOW}Note:${NC} Make sure to import the team configurations in AutoGen Studio before running tasks."
}

# Run main function
main "$@"
