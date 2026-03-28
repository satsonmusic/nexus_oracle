import time
from app.agents.orchestrator import run_agent

# Simple state memory for the worker
last_optimized_date = None

def get_current_date():
    return time.strftime("%Y-%m-%d")

print("Worker initialized...")

while True:
    current_date = get_current_date()
    
    # Only run the optimization once per day
    if last_optimized_date != current_date:
        print(f"Running autonomous day optimization for {current_date}...")
        result = run_agent("Review my calendar and optimize my day. Send me a summary.", "user_1")
        print(f"Result: {result['status']}")
        
        last_optimized_date = current_date
    
    # Sleep for an hour before checking again
    time.sleep(3600)