import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load from your secrets file
load_dotenv("infra/secrets.env")

class NexusGraph:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def add_causal_link(self, source: str, target: str, confidence: float):
        """Creates a verified causal relationship in the graph."""
        with self.driver.session() as session:
            session.execute_write(self._create_causal_relationship, source, target, confidence)

    @staticmethod
    def _create_causal_relationship(tx, source, target, confidence):
        # Cypher query to create nodes and a 'CAUSES' edge
        query = (
            "MERGE (a:Entity {name: $source}) "
            "MERGE (b:Entity {name: $target}) "
            "MERGE (a)-[r:CAUSES {confidence: $confidence}]->(b) "
            "RETURN r"
        )
        tx.run(query, source=source, target=target, confidence=confidence)

    def get_all_relations(self):
        """Retrieves every causal link stored in the graph for visualization."""
        query = """
        MATCH (s:Entity)-[r:CAUSES]->(t:Entity)
        RETURN s.name AS source, t.name AS target, r.confidence AS weight
        """
        with self.driver.session() as session:
            result = session.run(query)
            # Converting Neo4j records into a list of dictionaries for Streamlit
            return [{"source": record["source"], "target": record["target"], "weight": record["weight"]} 
                    for record in result]