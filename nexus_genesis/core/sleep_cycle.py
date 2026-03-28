import os
import sys
import re
import json
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.knowledge_graph import NexusGraph
from core.nodes import call_llm, judge_llm

graph = NexusGraph()

async def cognitive_sleep_cycle():
    print("--- [ BRAIN: INITIALIZING COGNITIVE SLEEP CYCLE ] ---")

    # 1. Load recent session data (filter for .md files only)
    output_dir = "output"
    if not os.path.exists(output_dir):
        print("Output folder not found. Sleep cycle skipped.")
        return

    reports = [f for f in os.listdir(output_dir) if f.endswith('.md')]

    if not reports:
        print("Nothing to consolidate. Sleep cycle skipped.")
        return

    latest_report = sorted(reports)[-1]
    with open(os.path.join(output_dir, latest_report), "r", encoding="utf-8") as f:
        content = f.read()

    # 2. Extract Causal Relationships using the Judge
    consolidation_prompt = (
        f"Analyze this research report:\n{content}\n\n"
        "Identify 3-5 permanent causal relationships (e.g., 'Entity A' -> causes -> 'Entity B'). "
        "Return ONLY a JSON list of objects: [{'source': '...', 'target': '...', 'weight': 0.0-1.0}]"
    )

    print("--- [ BRAIN: CONSOLIDATING FRAGMENTS INTO WISDOM ] ---")
    response = await call_llm(judge_llm, consolidation_prompt)

    try:
        clean_json = re.search(r"\[.*\]", response.content, re.DOTALL).group()
        links = json.loads(clean_json)

        # 3. Inject into Neo4j
        for link in links:
            source = link.get("source")
            target = link.get("target")
            weight = link.get("weight", 0.5)
            graph.add_causal_link(source, target, weight)
            print(f"Fused: ({source}) --[{weight}]--> ({target})")

        print("--- [ BRAIN: CONSOLIDATION COMPLETE. THE MONSTER IS SMARTER. ] ---")
    except Exception as e:
        print(f"Sleep Cycle Error: {e}")

if __name__ == "__main__":
    asyncio.run(cognitive_sleep_cycle())