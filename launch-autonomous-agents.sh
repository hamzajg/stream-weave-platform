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
