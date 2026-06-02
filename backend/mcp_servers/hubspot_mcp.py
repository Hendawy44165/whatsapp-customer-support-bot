import os
import sys
from mcp.server.fastmcp import FastMCP

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db

# Create FastMCP server
mcp = FastMCP("Nuit HubSpot CRM")

@mcp.tool()
def get_contact_profile(email: str) -> str:
    """
    Retrieves the HubSpot CRM customer profile by email.
    Returns contact details, lifecycle stage, and custom notes.
    """
    try:
        # Check if the customer has a history note in system or mock data
        # For simplicity, we search the conversations table for this email/phone, or return a mock profile
        db.add_system_log("hubspot_mcp", "INFO", f"Looking up CRM profile for: {email}")
        
        # Simple mock profiles based on common email addresses
        if "mariam" in email.lower():
            return (
                f"HubSpot Contact Found:\n"
                f"- Name: Mariam Hegazi\n"
                f"- Email: {email}\n"
                f"- Lifecycle Stage: Customer\n"
                f"- Notes: Purchased Discovery Box trial on 2026-06-01. Prefers WhatsApp notifications. Flagged as highly receptive to premium citrus notes."
            )
        elif "youssef" in email.lower():
            return (
                f"HubSpot Contact Found:\n"
                f"- Name: Youssef Aly\n"
                f"- Email: {email}\n"
                f"- Lifecycle Stage: Lead\n"
                f"- Notes: Initiated checkout but abandoned. Active ticket #8732 regarding order status. Emotion history: Frustrated."
            )
        else:
            return (
                f"HubSpot Contact Found:\n"
                f"- Name: Guest Client ({email})\n"
                f"- Email: {email}\n"
                f"- Lifecycle Stage: Lead\n"
                f"- Notes: No previous purchases or support tickets recorded."
            )
    except Exception as e:
        db.add_system_log("hubspot_mcp", "ERROR", f"Error in get_contact_profile for {email}: {str(e)}")
        return f"Error retrieving CRM profile: {str(e)}"

@mcp.tool()
def create_support_ticket(email: str, subject: str, description: str) -> str:
    """
    Creates a new support ticket in HubSpot CRM.
    Returns the ticket number and confirmation message.
    """
    try:
        db.add_system_log("hubspot_mcp", "INFO", f"Creating HubSpot ticket for {email}: {subject}")
        import random
        ticket_id = random.randint(10000, 99999)
        return (
            f"Successfully created HubSpot Support Ticket!\n"
            f"- Ticket ID: #HS-{ticket_id}\n"
            f"- Customer Email: {email}\n"
            f"- Subject: {subject}\n"
            f"- Description: {description}\n"
            f"- Status: OPEN (Assigned to General Support Queue)"
        )
    except Exception as e:
        db.add_system_log("hubspot_mcp", "ERROR", f"Error creating ticket: {str(e)}")
        return f"Error creating support ticket: {str(e)}"

if __name__ == "__main__":
    # Run the server on port 8011 using SSE transport
    import uvicorn
    # FastMCP exposes an ASGI application on .asgi_app
    uvicorn.run(mcp.asgi_app, host="0.0.0.0", port=8011)
