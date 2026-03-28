import os
import glob
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# Configuration for local LLM via Ollama
# Ensure Ollama is running and the model (e.g., qwen2.5-coder:7b or similar) is pulled
config_list = [
    {
        "model": "qwen2.5-coder:7b", # Or any other local model you have pulled in Ollama
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
    }
]

llm_config = {
    "config_list": config_list,
    "cache_seed": 42,
}

# 1. Define Agents
doc_reader = AssistantAgent(
    name="DocReader",
    system_message="""You are an expert Technical Analyst. 
Your task: Read the project documentation (provided in context) and extract:
1. Core features and functional requirements.
2. Technical constraints (ports, tech stack, architecture patterns).
3. Success criteria for the MVP.
Be concise but thorough. Output a structured requirement summary.""",
    llm_config=llm_config,
)

planner = AssistantAgent(
    name="Planner",
    system_message="""You are a Senior Project Manager and Product Owner.
Your task:
1. Take the requirements from DocReader.
2. Plan the product features and roadmap.
3. Decompose the project into iterations and manageable tasks.
4. Assign tasks to the Developer and Reviewer.
Focus on iterative delivery and clear task definitions.""",
    llm_config=llm_config,
)

architect = AssistantAgent(
    name="Architect",
    system_message="""You are a Lead Software Architect.
Your task:
1. Take the project plan and requirements.
2. Design the system architecture (e.g., Spring Boot, Actor Model, Reactor Bus).
3. Specify component interactions, data flows, and directory structure.
Ensure the design follows the 'System Blueprint' and 'Top-Down Problem Solving' docs.""",
    llm_config=llm_config,
)

developer = AssistantAgent(
    name="Developer",
    system_message="""You are a Senior Full-Stack Developer.
Your task:
1. Implement the features according to the Architect's design and Planner's tasks.
2. Write clean, production-ready code.
3. Organize code into the specified directory structure.
Only provide code blocks with file paths. No unnecessary conversational filler.""",
    llm_config=llm_config,
)

reviewer = AssistantAgent(
    name="Reviewer",
    system_message="""You are a Lead Code Reviewer.
Your task:
1. Review the code produced by the Developer.
2. Check for security vulnerabilities, efficiency, and adherence to the architecture.
3. Suggest improvements or approve the implementation.
Be critical but constructive.""",
    llm_config=llm_config,
)

user_proxy = UserProxyAgent(
    name="UserProxy",
    system_message="A human admin who triggers the project build. Can execute code and save files to disk.",
    code_execution_config={
        "work_dir": "build_output",
        "use_docker": False,
    },
    human_input_mode="NEVER",
)

# 2. Load documentation context
def load_docs(docs_dir="../docs"):
    doc_files = glob.glob(os.path.join(docs_dir, "*.md"))
    context = "PROJECT DOCUMENTATION:\n\n"
    for file_path in doc_files:
        with open(file_path, 'r') as f:
            context += f"--- {os.path.basename(file_path)} ---\n"
            context += f.read() + "\n\n"
    return context

# 3. Setup Group Chat
groupchat = GroupChat(
    agents=[user_proxy, doc_reader, planner, architect, developer, reviewer],
    messages=[],
    max_round=20,
)
manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# 4. Launch the Autonomous Team
if __name__ == "__main__":
    print("🚀 Launching the Autonomous AI Agents Team...")
    docs_context = load_docs()
    
    initial_prompt = f"""
START PROJECT BUILD.
Here is the documentation for the project:
{docs_context}

Team, please collaborate to:
1. Read the docs and summarize requirements (DocReader).
2. Plan the roadmap and iterations (Planner).
3. Architect the solution (Architect).
4. Decompose and implement the first iteration (Planner & Developer).
5. Review the code (Reviewer).
6. Save the results to the 'build_output' directory (UserProxy).
"""
    
    user_proxy.initiate_chat(
        manager,
        message=initial_prompt
    )
