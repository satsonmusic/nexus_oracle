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
    CODING RULE: If the user asks you to write, create, build, or implement any code, function, class, algorithm, or script — you MUST use 'respond_to_user' and write the complete working code directly in the message. Never use 'search_internet' for coding requests. Never say you will guide the user or provide steps. Just write the full working code immediately.
    KNOWLEDGE RULE: If you already know the answer to a factual question, use 'respond_to_user' directly. Only use 'search_internet' for current events, news, prices, or information that changes over time.
    """
    return parse_structured(prompt, Plan)
