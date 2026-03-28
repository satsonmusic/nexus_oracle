from app.services.llm import client

def stream_llm(prompt: str):
    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )
    for chunk in stream:
        if chunk.choices.delta.content is not None:
            yield chunk.choices.delta.content