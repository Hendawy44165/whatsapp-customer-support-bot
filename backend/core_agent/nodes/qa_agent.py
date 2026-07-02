from typing import Dict
from langchain_core.messages import SystemMessage, ToolMessage
from pydantic import BaseModel
from .base import BaseNode
from ..state import AgentState

class QAAgentNode(BaseNode):
    """
    Formulates a luxury brand-voice response for the customer.
    Follows WhatsApp formatting constraints and grounds output in RAG/CRM context.
    """
    def __call__(self, state: AgentState) -> Dict:
        system_prompt = self.agent.loader.load_prompt("qa_agent.md")
        
        rag_context = state.get("rag_output")
        learned_user_info = state.get("learned_user_info")
        router_decision = state.get("router_decision")
        react_state = state.get("react_state")
        emotion = router_decision.get("emotion") 
        classification = router_decision.get("classification")
        
        state_context_lines = []
        if rag_context:
            state_context_lines.append(f"RAG Context: {rag_context}")
        if learned_user_info:
            state_context_lines.append(f"Learned User Info: {learned_user_info}")

        if emotion:
            state_context_lines.append(f"Detected Emotion: {emotion}")
        if classification:
            state_context_lines.append(f"Message Classification: {classification}")
            
        if react_state:
            status_code = react_state.get("status_code", "not_triggered")
            if status_code and status_code != "failure":
                state_context_lines.append(f"React Status Code: {status_code}")
                
                if status_code == "success":
                    output = react_state.get("output")
                    if output:
                        state_context_lines.append(f"React Output: {output}")
                elif status_code == "incomplete_input":
                    missing_customer_data = react_state.get("missing_customer_data")
                    if missing_customer_data:
                        state_context_lines.append(f"Missing Customer Data: {missing_customer_data}")
                    query_rationale = react_state.get("query_rationale")
                    if query_rationale:
                        state_context_lines.append(f"Query Rationale: {query_rationale}")

        state_context = ""
        if state_context_lines:
            state_context = "#CONTEXT VARIABLES\n" + "".join(state_context_lines)
            
        # Prepare inputs
        messages = [SystemMessage(content=system_prompt)]
        if state_context:
            messages.append(SystemMessage(content=state_context))
            
        # Include recent message history
        history = state.get("messages", [])
        messages.extend(history)
        
        # Define search tool
        search_tool = {
            "type": "function",
            "function": {
                "name": "retrieve_knowledge",
                "description": (
                    "Search Nuit Fragrances official policies, terms, FAQs, product specs, and brand guidelines. "
                    "Use this tool to find information about shipping times, shipping fees, returns, exchanges, "
                    "damaged items, product specs, and general brand FAQs."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query. Reformulate based on conversation history if necessary.",
                        }
                    },
                    "required": ["query"],
                },
            }
        }
        
        # Bind tool to model
        model_with_tools = self.agent.model.bind_tools([search_tool])
        
        max_steps = 2
        step = 0
        rag_retrieved_contexts = []
        rag_queries_made = []
        active_messages = list(messages)
        
        while step < max_steps:
            response = model_with_tools.invoke(active_messages)
            
            if not response.tool_calls:
                break
                
            active_messages.append(response)
            for tool_call in response.tool_calls:
                if tool_call["name"] == "retrieve_knowledge":
                    query = tool_call["args"].get("query")
                    rag_queries_made.append(query)
                    context = self.agent.loader.retrieve_context(query)
                    if context:
                        rag_retrieved_contexts.append(context)
                        
                    tool_msg = ToolMessage(
                        content=context if context else "No relevant information found in knowledge base.",
                        tool_call_id=tool_call["id"]
                    )
                    active_messages.append(tool_msg)
            step += 1
        else:
            response = model_with_tools.invoke(active_messages)
            
        updates = { "messages": [response] }
        
        # Track the search queries generated by the agent
        updates["agent_queries"] = ", ".join(rag_queries_made) if rag_queries_made else ""
        
        # If any context was retrieved, update the state's rag_output
        if rag_retrieved_contexts:
            updates["rag_output"] = "\n\n---\n\n".join(rag_retrieved_contexts)
            
        # Determine if the agent is transferring the user
        transfer_keywords = ["transfer", "specialist", "representative", "human agent", "care team", "reconnect", "unable to locate"]
        content_lower = response.content.lower() if response.content else ""
        is_transferring = any(kw in content_lower for kw in transfer_keywords)
            
        combined_rag = rag_context or updates.get("rag_output", "")
        if not combined_rag or not combined_rag.strip() or is_transferring:
            updates["process_state"] = "no_info_found"
            
        return updates
