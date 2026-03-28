from app.services.llm import parse_structured
from app.schemas import Review

def review(user_input: str, results: list) -> Review:
    prompt = f"""
    Evaluate if the executed steps successfully answered the user's request.
    User Request: {user_input}
    Execution Results: {results}
    
    Determine if this is a success, and provide brief feedback.
    """
    return parse_structured(prompt, Review)