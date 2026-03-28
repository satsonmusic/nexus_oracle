import datetime
from app.services.llm import parse_structured
from app.schemas import Plan

def plan(user_input: str, context: str, feedback: str = "") -> Plan:
    # Give Jarvis the current exact time so he can calculate "tomorrow" or "next week"
    current_time = datetime.datetime.now().astimezone().strftime("%A, %B %d, %Y at %I:%M %p %Z")
    
    prompt = f"""
    You are Jarvis, an elite AI assistant. Break the user's request into actionable tool steps.
    
    Current System Time: {current_time}
    User Request: {user_input}
    Memory Context: {context}
    Previous Feedback (if any): {feedback}
    
    Available tools: 
    - 'create_event': Requires 'title', 'start_time' (ISO 8601), 'end_time' (ISO 8601), and optional 'description'. Always use UTC time ('Z').
    - 'list_upcoming_events': Requires 'max_results' (integer).
    - 'send_email': Requires 'to_email' (string), 'subject' (string), and 'body' (string).
    - 'read_recent_emails': Requires 'max_results' (integer).
    - 'search_internet': Requires 'query' (string). Use this to search the web for facts, news, or general knowledge.
    - 'respond_to_user': Requires 'message' (string). Use this to talk back to the user or provide answers directly.
    
    CRITICAL: You must return valid JSON matching the Plan schema. ONLY use the exact tool names listed above. Do not invent tools.
    """
    return parse_structured(prompt, Plan)