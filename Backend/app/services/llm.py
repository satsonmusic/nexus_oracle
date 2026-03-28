import os
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("CRITICAL ERROR: 'OPENAI_API_KEY' not found in your environment variables.")

client = OpenAI(api_key=api_key)

def chat(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices.message.content

def parse_structured(prompt: str, response_model: type[BaseModel]) -> BaseModel:
    """Forces the LLM to output valid JSON matching the Pydantic model."""
    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format=response_model
    )
    return response.choices[0].message.parsed 