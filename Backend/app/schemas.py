from pydantic import BaseModel, Field
from typing import List

class Step(BaseModel):
    tool: str
    inputs: str = Field(description="A JSON-formatted string containing the arguments for the tool.")

class Plan(BaseModel):
    thoughts: str
    steps: List[Step]

class Review(BaseModel):
    success: bool
    feedback: str