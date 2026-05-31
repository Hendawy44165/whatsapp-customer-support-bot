import os
import glob
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable

class CustomerServiceAgent:
    def __init__(self, docs_dir="agent/docs", prompt_path="agent/prompts/system_prompt.md", model_name="gemini-2.5-flash"):
        self.docs_dir = docs_dir
        self.prompt_path = prompt_path
        self.model_name = model_name
        
        # Load the knowledge base and system prompt
        self.knowledge_base = self._load_knowledge_base()
        self.system_prompt = self._load_system_prompt()
        
        # Build the final system instruction for the React agent
        self.system_instruction = f"{self.system_prompt}\n\nRefer to the following knowledge base for all answers, rules, and procedures:\n{self.knowledge_base}"
        
        # Initialize the LangChain Google model
        self.model = ChatGoogleGenerativeAI(model=self.model_name)
        
        # Initialize memory checkpointer
        self.memory = MemorySaver()
        
        # Config for memory scoping
        self.config = {"configurable": {"thread_id": "default-thread"}}
        
        # Create prebuilt React Agent using create_agent
        self.agent = create_agent(
            model=self.model,
            tools=[],
            checkpointer=self.memory,
            system_prompt=self.system_instruction
        )

    def _load_knowledge_base(self):
        kb_text = []
        md_files = glob.glob(os.path.join(self.docs_dir, "*.md"))
        for filepath in sorted(md_files):
            filename = os.path.basename(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                kb_text.append(f"\n--- Document: {filename} ---\n{content}\n")
        return "\n".join(kb_text)

    def _load_system_prompt(self):
        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    @traceable
    def send_message(self, message: str) -> str:
        inputs = {"messages": [("user", message)]}
        response = self.agent.invoke(inputs, config=self.config)
        return response["messages"][-1].content

    def get_history(self):
        state = self.agent.get_state(self.config)
        return state.values.get("messages", [])
