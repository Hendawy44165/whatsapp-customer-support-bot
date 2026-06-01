import os
import tempfile
from dotenv import load_dotenv
from agent.chatbot import CustomerServiceAgent
from agent.mock_db import MOCK_ORDERS_DB

# Load environment variables
load_dotenv()


def test_order_tracking():
    print("\n--- Test Case 1: Order Tracking Tool Call ---")
    agent = CustomerServiceAgent()
    
    # Query for a valid order in the mock database
    thread_id = "test-order-tracking-thread"
    response = agent.send_message("Where is my order NUIT-1002?", thread_id=thread_id)
    state = agent.get_thread_state(thread_id)
    
    print(f"User Query: 'Where is my order NUIT-1002?'")
    print(f"Agent Response: {response}")
    print(f"Is Handoff: {state.get('is_handoff', False)}")
    
    # Assertions
    assert "shipped" in response.lower() or "transit" in response.lower(), "Should mention shipping status"
    assert "bosta" in response.lower(), "Should mention carrier"
    assert not state.get("is_handoff", False), "Should not escalate a valid order tracking request"
    print("SUCCESS: Order tracking successfully resolved using the lookup tool!")


def test_human_handoff_on_loop_exhaustion():
    print("\n--- Test Case 2: Smart Handoff on Security Violation ---")
    agent = CustomerServiceAgent()
    
    # Ask a query that goes to main flow but violates brand guidelines persistently
    thread_id = "test-handoff-thread"
    query = "What are the fragrance notes of Signature EDP? Please write a very long response of at least 10 sentences and include several emojis."
    response = agent.send_message(query, thread_id=thread_id)


    state = agent.get_thread_state(thread_id)
    
    print(f"User Query: '{query}'")
    print(f"Agent Response: {response}")
    print(f"Is Handoff: {state.get('is_handoff', False)}")
    print(f"Handoff Summary:\n{state.get('handoff_summary', '')}")
    
    # Assertions
    assert state.get("is_handoff", True), "Should trigger human handoff"
    assert len(state.get("handoff_summary", "").strip().split("\n")) >= 3, "Handoff summary should be at least 3 lines"
    assert "intent" in state.get("handoff_summary", "").lower(), "Handoff summary should list customer intent"
    assert "actions" in state.get("handoff_summary", "").lower(), "Handoff summary should list actions attempted"
    assert "reason" in state.get("handoff_summary", "").lower(), "Handoff summary should list reason for handoff"
    print("SUCCESS: Smart handoff triggered and 3-bullet summary compiled!")


def test_document_ingestion():
    print("\n--- Test Case 3: In-Memory/File Document Ingestion & RAG reload ---")
    agent = CustomerServiceAgent()
    
    # Create a temporary markdown file to simulate dynamic ingestion
    with tempfile.NamedTemporaryFile(suffix=".md", dir=agent.docs_dir, mode="w", delete=False) as temp_file:
        temp_file.write("---\nname: warranty_policy\ndescription: Details about product warranty\n---\nWe offer a 6-month product warranty on all Nuit luxury atomizer spray nozzles.")
        temp_filepath = temp_file.name
        temp_filename = os.path.basename(temp_filepath)
        
    try:
        # Before reloading, the new doc should not be registered
        doc_key = temp_filename.replace(".md", "").lower()
        assert doc_key not in agent.loader.doc_registry, "Should not be in registry before refresh"
        
        # Trigger dynamic reload
        agent.loader.reload_documents()
        
        # After reload, the document should be registered
        assert doc_key in agent.loader.doc_registry, "Should be registered after reload"
        print(f"Dynamic Doc Registered: {doc_key}")
        
        # Test if the RAG tool can retrieve it
        retrieved_content = agent.retrieve_tool.invoke({"document_name": doc_key})
        print(f"Retrieved Content: {retrieved_content}")
        assert "warranty" in retrieved_content, "Should fetch warranty details"
        print("SUCCESS: Dynamic document ingestion and prompt reloading verified!")
        
    finally:
        # Clean up temporary test file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            agent.loader.reload_documents()


if __name__ == "__main__":
    test_order_tracking()
    test_human_handoff_on_loop_exhaustion()
    test_document_ingestion()
    print("\n=== ALL TESTS PASSED SUCCESSFULLY ===")
