FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy nexus_genesis pipeline first (will be in repo root)
COPY nexus_genesis/ ./nexus_genesis/

# Copy Jarvis backend
COPY Backend/ ./Backend/

WORKDIR /app/Backend

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    sqlalchemy[asyncio] \
    asyncpg \
    aiosqlite \
    "redis[asyncio]" \
    openai \
    pydantic \
    python-dotenv \
    numpy \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib \
    duckduckgo-search \
    langchain \
    langchain-openai \
    langchain-community \
    langgraph \
    langchain-tavily \
    langchain-experimental \
    presidio-analyzer \
    presidio-anonymizer \
    spacy \
    deepeval \
    neo4j \
    lancedb \
    z3-solver \
    arxiv \
    scipy \
    scikit-learn \
    matplotlib \
    ddgs \
    websockets \
    streamlit

RUN python -m spacy download en_core_web_lg

# Set NEXUS_ROOT to the bundled pipeline
ENV NEXUS_ROOT=/app/nexus_genesis

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
