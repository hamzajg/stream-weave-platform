import os
import glob
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from termcolor import colored
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AutonomousMesh")

@dataclass
class MeshConfig:
    model: str = "qwen2.5-coder:7b" # Optimized for local coding tasks
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    docs_path: str = "../docs"
    workspace_path: str = "workspace"
    max_rounds: int = 30

class AutonomousMesh:
    def __init__(self, config: MeshConfig):
        self.config = config
        self.llm_config = {
            "config_list": [{"model": config.model, "base_url": config.base_url, "api_key": config.api_key}],
            "cache_seed": 42,
            "temperature": 0.1, # Low temperature for consistency
        }
        self._ensure_workspace()
        self.agents = self._setup_agents()
        self.manager = self._setup_orchestration()

    def _ensure_workspace(self):
        if not os.path.exists(self.config.workspace_path):
            os.makedirs(self.config.workspace_path)
            logger.info(f"Created workspace: {self.config.workspace_path}")

    def _setup_agents(self) -> Dict[str, Any]:
        """Initialize sophisticated agent personas with specialized prompts."""
        
        # 1. Product Manager (The Orchestrator/Planner)
        pm = AssistantAgent(
            name="ProductManager",
            system_message="""You are a Senior Technical Product Manager.
Your role: 
1. Lead the team in decomposing high-level requirements into clear, technical tasks.
2. Maintain the project roadmap and ensure alignment with the docs.
3. Manage the 'backlog' of tasks and assign them to the Architect or Developer.
4. Synthesize reports from other agents to determine the next logical step.
You output task lists and project plans in structured markdown.""",
            llm_config=self.llm_config,
        )

        # 2. System Architect (The Designer)
        architect = AssistantAgent(
            name="SystemArchitect",
            system_message="""You are a Principal Software Architect specializing in Reactive Systems and Microservices.
Your role:
1. Design the technical architecture based on the PM's requirements.
2. Specify directory structures, class hierarchies, and API endpoints.
3. Ensure the design follows best practices (e.g., SOLID, Actor Model, SSE).
4. Provide detailed 'design blueprints' for the Developer to follow.
Refer to the 'System Blueprint' and 'Top-Down' docs in the context.""",
            llm_config=self.llm_config,
        )

        # 3. Lead Developer (The Implementer)
        developer = AssistantAgent(
            name="LeadDeveloper",
            system_message="""You are an Elite Software Engineer proficient in Java, Spring Boot, and Python.
Your role:
1. Implement the architecture designed by the Architect.
2. Write production-grade code with error handling and logging.
3. Organize files correctly in the workspace.
4. Output FULL file contents in markdown code blocks with the file path specified.
Example: 
```java
// filepath: src/main/java/com/app/Main.java
public class Main { ... }
```""",
            llm_config=self.llm_config,
        )

        # 4. Code Reviewer (The Quality Gate)
        reviewer = AssistantAgent(
            name="CodeReviewer",
            system_message="""You are a Senior QA and Security Engineer.
Your role:
1. Audit the code and design produced by the team.
2. Check for security flaws, race conditions, and performance bottlenecks.
3. Verify that the implementation matches the Architect's blueprint.
4. Provide a 'Pass/Fail' report with specific improvement points.
If a task fails, specify EXACTLY what needs to be fixed.""",
            llm_config=self.llm_config,
        )

        # 5. User Proxy (The Local Executor)
        proxy = UserProxyAgent(
            name="UserProxy",
            system_message="""A local execution engine that handles file I/O and command execution.
It will save the code blocks produced by the Developer to the 'workspace' directory.""",
            code_execution_config={
                "work_dir": self.config.workspace_path,
                "use_docker": False,
            },
            human_input_mode="NEVER",
        )

        return {
            "pm": pm,
            "architect": architect,
            "developer": developer,
            "reviewer": reviewer,
            "proxy": proxy
        }

    def _setup_orchestration(self) -> GroupChatManager:
        """Setup the mesh coordination logic."""
        groupchat = GroupChat(
            agents=list(self.agents.values()),
            messages=[],
            max_round=self.config.max_rounds,
            speaker_selection_method="auto", # Allows the LLM to choose the next agent based on the state
            allow_repeat_speaker=False
        )
        return GroupChatManager(groupchat=groupchat, llm_config=self.llm_config)

    def _load_docs(self) -> str:
        """Load documentation as context for the mesh."""
        doc_files = glob.glob(os.path.join(self.config.docs_path, "*.md"))
        context = "### PROJECT CORE CONTEXT (INITIAL DOCS) ###\n\n"
        for file_path in doc_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    context += f"#### FILE: {os.path.basename(file_path)} ####\n{content}\n\n"
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
        return context

    def launch(self):
        """Trigger the autonomous mesh to build the solution."""
        print(colored("\n" + "="*60, "cyan"))
        print(colored("🚀 STREAM-WEAVE AUTONOMOUS MESH LAUNCHING...", "cyan", attrs=["bold"]))
        print(colored("="*60 + "\n", "cyan"))
        
        context = self._load_docs()
        initial_prompt = f"""
{context}

### OBJECTIVE: BUILD THE STREAMWEAVE PLATFORM ###

Team, you are tasked with implementing the full StreamWeave Platform as described in the docs.
This is an advanced implementation. Follow this structured workflow:

1. **PM**: Analyze the docs and define the MVP Iteration 1 (Core Actor Mesh).
2. **Architect**: Design the internal directory structure and core interfaces for the API Gateway.
3. **Developer**: Implement the API Gateway code (Spring Boot) and the Reactor Message Bus.
4. **Reviewer**: Audit the implementation for architectural alignment.
5. **UserProxy**: Ensure all files are persisted to the 'workspace' folder.

PM, start by presenting the project roadmap and the first set of tasks.
"""
        self.agents["proxy"].initiate_chat(
            self.manager,
            message=initial_prompt
        )

if __name__ == "__main__":
    config = MeshConfig()
    mesh = AutonomousMesh(config)
    mesh.launch()
