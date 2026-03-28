from app.memory.vector import search, store

def build_context(query: str, user_id: str) -> str:
    """Retrieves relevant past memories before Jarvis makes a plan."""
    return search(query)

def store_memory(user_input: str, result: str):
    """Saves the completed action to Jarvis's long-term memory."""
    store(f"User asked: '{user_input}' | Jarvis executed: {result}")