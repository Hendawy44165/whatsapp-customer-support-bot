"""
HubSpot Free CRM integration via REST API.

Credentials:
    Set HUBSPOT_ACCESS_TOKEN in .env (get from HubSpot > Settings > Private Apps).
    Without a token, all calls are stubbed and logged as warnings.

API Reference:
    Contacts: https://developers.hubspot.com/docs/api/crm/contacts
    Notes (Engagements): https://developers.hubspot.com/docs/api/crm/engagements
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger('hubspot_client')

HUBSPOT_ACCESS_TOKEN = os.getenv('HUBSPOT_ACCESS_TOKEN', '')
HUBSPOT_API_BASE = 'https://api.hubapi.com'


def _headers() -> dict:
    return {
        'Authorization': f'Bearer {HUBSPOT_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }


def _is_configured() -> bool:
    if not HUBSPOT_ACCESS_TOKEN:
        logger.warning('[STUB] HubSpot not configured. Set HUBSPOT_ACCESS_TOKEN in .env.')
        return False
    return True


def upsert_contact(phone: str, name: Optional[str] = None, email: Optional[str] = None) -> Optional[str]:
    """
    Create or update a HubSpot Contact by phone number.
    
    Uses the HubSpot Contacts search API to find existing contact,
    then creates or updates accordingly.
    
    Args:
        phone: Customer phone number (used as unique identifier)
        name: Customer display name (optional)
        email: Customer email (optional)
    
    Returns:
        HubSpot contact ID string, or None if not configured / on error
    """
    if not _is_configured():
        logger.info('[STUB] upsert_contact called for phone=%s name=%s', phone, name)
        return 'stub_contact_id'
    
    # Search for existing contact by phone
    search_url = f'{HUBSPOT_API_BASE}/crm/v3/objects/contacts/search'
    search_payload = {
        'filterGroups': [{
            'filters': [{
                'propertyName': 'phone',
                'operator': 'EQ',
                'value': phone
            }]
        }],
        'properties': ['phone', 'firstname', 'email']
    }
    
    try:
        search_resp = requests.post(search_url, json=search_payload, headers=_headers(), timeout=10)
        search_resp.raise_for_status()
        results = search_resp.json().get('results', [])
        
        properties = {'phone': phone}
        if name:
            # Try to split name into first/last
            parts = name.strip().split(' ', 1)
            properties['firstname'] = parts[0]
            if len(parts) > 1:
                properties['lastname'] = parts[1]
        if email:
            properties['email'] = email
        
        if results:
            # Update existing contact
            contact_id = results[0]['id']
            update_url = f'{HUBSPOT_API_BASE}/crm/v3/objects/contacts/{contact_id}'
            requests.patch(update_url, json={'properties': properties}, headers=_headers(), timeout=10)
            logger.info('HubSpot: Updated contact %s for phone %s', contact_id, phone)
            return contact_id
        else:
            # Create new contact
            create_url = f'{HUBSPOT_API_BASE}/crm/v3/objects/contacts'
            create_resp = requests.post(create_url, json={'properties': properties}, headers=_headers(), timeout=10)
            create_resp.raise_for_status()
            contact_id = create_resp.json()['id']
            logger.info('HubSpot: Created contact %s for phone %s', contact_id, phone)
            return contact_id
    
    except Exception as e:
        logger.error('HubSpot upsert_contact failed: %s', str(e))
        return None


def log_note(contact_id: str, body: str) -> Optional[str]:
    """
    Log a Note on a HubSpot contact (via Engagements API).
    
    Args:
        contact_id: HubSpot contact ID
        body: Note body text
    
    Returns:
        HubSpot note/engagement ID, or None on error
    """
    if not _is_configured():
        logger.info('[STUB] log_note called for contact=%s body=%s', contact_id, body[:80])
        return 'stub_note_id'
    
    url = f'{HUBSPOT_API_BASE}/crm/v3/objects/notes'
    payload = {
        'properties': {
            'hs_note_body': body,
            'hs_timestamp': str(int(__import__('time').time() * 1000))
        },
        'associations': [{
            'to': {'id': contact_id},
            'types': [{
                'associationCategory': 'HUBSPOT_DEFINED',
                'associationTypeId': 202  # Note to Contact
            }]
        }]
    }
    
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=10)
        resp.raise_for_status()
        note_id = resp.json()['id']
        logger.info('HubSpot: Logged note %s on contact %s', note_id, contact_id)
        return note_id
    except Exception as e:
        logger.error('HubSpot log_note failed: %s', str(e))
        return None


def log_conversation_summary(phone: str, summary: str, intent: str = '', sentiment: str = '') -> None:
    """
    Convenience function: upsert contact and log a conversation summary note.
    Called at the end of every AI conversation turn.
    
    Args:
        phone: Customer phone number
        summary: Conversation summary or escalation reason
        intent: Detected intent (optional)
        sentiment: Detected sentiment (optional)
    """
    contact_id = upsert_contact(phone)
    if contact_id:
        note_body = f'WhatsApp Conversation Summary\n'
        if intent:
            note_body += f'Intent: {intent}\n'
        if sentiment:
            note_body += f'Sentiment: {sentiment}\n'
        note_body += f'Summary: {summary}'
        log_note(contact_id, note_body)
