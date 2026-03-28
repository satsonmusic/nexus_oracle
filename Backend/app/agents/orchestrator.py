from app.agents.planner import plan
from app.agents.executor import execute
from app.agents.reviewer import review
from app.memory.manager import build_context, store_memory

def run_agent(user_input: str, user_id: str):
    context = build_context(user_input, user_id)
    
    max_retries = 3
    attempt = 0
    feedback = ""

    while attempt < max_retries:
        # 1. Plan (incorporating any previous feedback)
        current_plan = plan(user_input, context, feedback)
        
        # 2. Execute
        results = execute(current_plan.steps)
        
        # 3. Review
        review_result = review(user_input, results)
        
        if review_result.success:
            store_memory(user_input, str(results))
            return {
                "status": "success",
                "plan": current_plan.model_dump(),
                "results": results
            }
        
        # If failed, generate feedback and loop again
        feedback = f"Previous attempt failed. Feedback: {review_result.feedback}. Results were: {results}"
        attempt += 1

    return {"status": "failed", "message": "Max retries reached.", "final_feedback": feedback}