import os
from app.agents.orchestrator import run_agent

def terminal_chat():
    print("========================================")
    print("🧠 Jarvis is online. Type 'exit' to quit.")
    print("========================================\n")
    
    while True:
        # Get your input
        command = input("🗣️ You: ")
        
        if command.lower() == 'exit':
            print("Shutting down...")
            break
            
        print("🤖 Jarvis is thinking...\n")
        
        # Send to Jarvis
        result = run_agent(command, "scott_123")
        
        # Print the results
        if result["status"] == "success":
            for step in result['results']:
                print(f"✅ {step['tool']} executed successfully.")
                print(f"   Output: {step['output']}\n")
        else:
            print(f"❌ Error: {result}")

if __name__ == "__main__":
    terminal_chat()