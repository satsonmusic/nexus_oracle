import json
from app.tools.registry import TOOLS
from app.schemas import Step
from typing import List

def execute(steps: List[Step]):
    results = []
    for step in steps:
        tool_name = step.tool
        if tool_name in TOOLS:
            try:
                # Convert the JSON string back into a Python dictionary
                kwargs = json.loads(step.inputs)
                
                # Unpack the dictionary into the tool function
                res = TOOLS[tool_name](**kwargs)
                results.append({"tool": tool_name, "status": "success", "output": res})
            except Exception as e:
                results.append({"tool": tool_name, "status": "error", "error": str(e)})
        else:
            results.append({"tool": tool_name, "status": "error", "error": "Tool not found"})
    return results