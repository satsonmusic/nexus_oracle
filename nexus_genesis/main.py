import asyncio
from core.orchestrator import create_nexus_graph

async def main():
    # Initialize the "Nervous System"
    app = create_nexus_graph()
    
    # THE SURGICAL GHOST TASK:
    # We frame this technically to see if the Nexus can find a "Mechanism"
    # for paranormal claims using 2026 acoustic research.
    initial_state = {
        "task": (
            "Analyze the 'Infrasound Hallucination Hypothesis': Can neuro-symbolic AI "
            "differentiate between 19Hz frequency-induced visual distortions and "
            "anomalous atmospheric entities in reported 'haunted' locations?"
        ),
        "plan": [],
        "iterations": 0,
        "uncertainty_flags": [],
        "confidence_score": 0.0
    }

    print("--- NEXUS: PARANORMAL INVESTIGATION INITIALIZING ---")
    print(f"TASK: {initial_state['task']}\n")

    # Run the iterative loop
    async for event in app.astream(initial_state):
        for node, state_update in event.items():
            # This prints the active node's logic to your terminal
            print(state_update)
            print("-" * 50)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n--- NEXUS: SHUTTING DOWN ---")
    except Exception as e:
        print(f"\n[CRITICAL ERROR]: {e}")