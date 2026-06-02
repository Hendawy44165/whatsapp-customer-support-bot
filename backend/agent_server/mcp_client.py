import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional
from mcp import ClientSession
from mcp.client.sse import sse_client

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db

logger = logging.getLogger("mcp_client")

# Define target MCP server SSE endpoints
MCP_ENDPOINTS = {
    "hubspot": "http://localhost:8011/sse",
    "shop_cart": "http://localhost:8012/sse",
    "conversations": "http://localhost:8013/sse",
    "human_expert": "http://localhost:8014/sse"
}

class MCPClientManager:
    """
    Manages connections and calls to the 4 MCP tools sub-servers.
    If the servers are offline, automatically routes tool executions
    to local fallback python modules to keep the system runnable.
    """
    def __init__(self):
        # Determine if we should attempt network calls
        self.loop = asyncio.get_event_loop()

    def _run_async(self, coro):
        """Helper to run async coroutines synchronously."""
        try:
            if self.loop.is_running():
                # If loop is already running, run in a separate thread or use nest_asyncio
                import nest_asyncio
                nest_asyncio.apply()
                return asyncio.run_coroutine_threadsafe(coro, self.loop).result()
            else:
                return self.loop.run_until_complete(coro)
        except Exception as e:
            # Fallback if loop issues occur
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

    async def _call_mcp_sse(self, server_key: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Establishes a dynamic connection to the SSE server and calls the specified tool."""
        url = MCP_ENDPOINTS[server_key]
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return result.content[0].text

    def call_tool(self, server_key: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Synchronous entry point to execute a tool.
        Attempts to call the live MCP server over SSE. If it fails (e.g. server is down),
        it falls back to direct local execution.
        """
        try:
            logger.info(f"MCPClientManager: Calling {tool_name} on {server_key} server...")
            return self._run_async(self._call_mcp_sse(server_key, tool_name, arguments))
        except Exception as err:
            logger.warning(f"MCPClientManager: {server_key} server unreachable ({err}). Executing local fallback...")
            return self.execute_local_fallback(server_key, tool_name, arguments)

    def execute_local_fallback(self, server_key: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Mock/Fallback execution directly invoking local logic when sub-servers are offline.
        """
        # --- HubSpot Fallback ---
        if server_key == "hubspot":
            email = arguments.get("email", "guest@nfragrances.com")
            if tool_name == "get_contact_profile":
                if "mariam" in email.lower():
                    return "Fallback Profile: Mariam Hegazi. Prefers WhatsApp. Purchased Discovery Box."
                return f"Fallback Profile: Lead ({email}). No purchase history."
            elif tool_name == "create_support_ticket":
                return f"Fallback Ticket Created #HS-FB-12938 for {email}"

        # --- Shop Cart Fallback ---
        elif server_key == "shop_cart":
            conversation_id = arguments.get("conversation_id", "fallback_id")
            if tool_name == "list_products":
                from mcp_servers.shop_cart_mcp import list_products
                return list_products()
            elif tool_name == "add_to_cart":
                from mcp_servers.shop_cart_mcp import add_to_cart
                return add_to_cart(conversation_id, arguments.get("product_code", ""), arguments.get("quantity", 1))
            elif tool_name == "edit_cart":
                from mcp_servers.shop_cart_mcp import edit_cart
                return edit_cart(conversation_id, arguments.get("product_code", ""), arguments.get("quantity", 0))
            elif tool_name == "get_cart":
                from mcp_servers.shop_cart_mcp import get_cart
                return get_cart(conversation_id)
            elif tool_name == "generate_cart_report":
                from mcp_servers.shop_cart_mcp import generate_cart_report
                return generate_cart_report(conversation_id)

        # --- Conversations Fallback ---
        elif server_key == "conversations":
            conversation_id = arguments.get("conversation_id", "fallback_id")
            if tool_name == "get_chat_history":
                messages = db.get_messages(conversation_id)
                lines = []
                for m in messages:
                    lines.append(f"{m['sender_type']}: {m['content']}")
                return "\n".join(lines) if lines else "Empty chat history"
            elif tool_name == "queue_immediate_message":
                db.queue_outbound_message(conversation_id, arguments.get("content", ""))
                return "Immediate message queued."
            elif tool_name == "queue_scheduled_followup":
                # Convert seconds to timestamp
                delay = arguments.get("delay_seconds", 60)
                import datetime
                future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay)
                db.queue_outbound_message(conversation_id, arguments.get("content", ""), scheduled_for=future.isoformat())
                return f"Follow-up scheduled in {delay} seconds."

        # --- Human Expert Fallback ---
        elif server_key == "human_expert":
            conversation_id = arguments.get("conversation_id", "fallback_id")
            if tool_name == "request_human_handoff":
                from mcp_servers.human_expert_mcp import request_human_handoff
                return request_human_handoff(conversation_id, arguments.get("handoff_summary", ""))

        return f"Fallback error: Tool {tool_name} not found on server {server_key}."

# Global client manager instance
mcp_client = MCPClientManager()
