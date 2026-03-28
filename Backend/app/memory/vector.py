# backend/app/memory/vector.py
import numpy as np
from app.services.llm import client

# In-memory vector store: list of dicts {"text": str, "embedding": np.array}
vector_store = []

def get_embedding(text: str):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return np.array(response.data[0].embedding)

def store(text: str):
    vector = get_embedding(text)
    vector_store.append({"text": text, "embedding": vector})

def search(query: str, top_k: int = 2) -> str:
    if not vector_store:
        return "No prior memory."
    
    query_vector = get_embedding(query)
    similarities = [np.dot(query_vector, item["embedding"]) for item in vector_store]
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    
    results = [vector_store[i]["text"] for i in top_indices]
    return "\n".join(results)