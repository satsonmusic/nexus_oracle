import os
import uuid
import lancedb
import pandas as pd
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from dotenv import load_dotenv

# 1. Initialize the environment
load_dotenv("infra/secrets.env")

# 2. Setup the Embedding Registry
# We use OpenAI's small model for fast, efficient vectorization
embeddings = get_registry().get("openai").create(
    name="text-embedding-3-small"
)

class ResearchEntry(LanceModel):
    """The schema for a piece of semantic memory."""
    id: str
    text: str = embeddings.SourceField()
    # OpenAI 'small' model produces 1536-dimensional vectors
    vector: Vector(1536) = embeddings.VectorField()
    metadata: str

class NexusVectorStore:
    def __init__(self, db_path="data/nexus_vectors"):
        """Initializes the local vector database and the research table."""
        os.makedirs("data", exist_ok=True)
        
        self.db = lancedb.connect(db_path)
        self.table_name = "research_library" # Unified Table Name
        
        if self.table_name not in self.db.table_names():
            self.table = self.db.create_table(self.table_name, schema=ResearchEntry)
        else:
            self.table = self.db.open_table(self.table_name)

    def add_finding(self, text: str, metadata: str = "general"):
        """Embeds and stores a verified research finding."""
        data = [
            {
                "id": str(uuid.uuid4()), 
                "text": text, 
                "metadata": metadata
            }
        ]
        self.table.add(data)
        print(f"--- [ VECTOR STORE: INGESTED SEMANTIC FINDING ] ---")

    def search(self, query: str, limit: int = 3):
        """Returns results as a Pandas DataFrame (Ideal for Dashboard/Debugging)."""
        return self.table.search(query).limit(limit).to_pandas()

    def search_findings(self, query: str, limit: int = 3):
        """Returns results as a list of strings (Ideal for the Librarian's context)."""
        # We use self.table here to ensure we search the same data we just added
        results = self.table.search(query).limit(limit).to_list()
        return [r['text'] for r in results]