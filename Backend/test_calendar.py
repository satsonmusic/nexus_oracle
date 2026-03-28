import datetime
from app.tools.calendar import create_event, list_upcoming_events

def run_test():
    print("Initializing Jarvis Calendar Test...\n")
    
    # 1. Test Event Creation (Scheduling a test event for tomorrow)
    tomorrow = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    start_time = tomorrow.replace(hour=10, minute=0, second=0).isoformat() + 'Z'
    end_time = tomorrow.replace(hour=11, minute=0, second=0).isoformat() + 'Z'
    
    print("Attempting to create a test event...")
    creation_result = create_event(
        title="🤖 Jarvis Initial Boot Test",
        start_time=start_time,
        end_time=end_time,
        description="Testing OAuth connection and calendar write permissions."
    )
    print(f"Result: {creation_result}\n")
    
    # 2. Test Event Retrieval
    print("Attempting to fetch upcoming schedule...")
    retrieval_result = list_upcoming_events(max_results=3)
    print(retrieval_result)

if __name__ == "__main__":
    run_test()