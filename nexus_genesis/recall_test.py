from memory.vector_store import NexusVectorStore
from memory.knowledge_graph import NexusGraph

def test_recall():
    print("--- [ RECALL: TESTING SYSTEM MEMORY ] ---")
    
    # 1. Test Semantic Recall (LanceDB)
    try:
        vector_library = NexusVectorStore()
        query = "How does AI help scientific reproducibility?"
        results = vector_library.search(query, limit=1)
        
        print("\n[ SEMANTIC LIBRARY RECALL ]")
        if not results.empty:
            # Bulletproof Access: Get the 'text' column, then the first value
            matched_text = results["text"].values
            print(f"Found match: {matched_text}")
        else:
            print("No semantic matches found. Did you run main.py first?")
    except Exception as e:
        print(f"Error recalling from Vector Store: {e}")

    # 2. Test Causal Recall (Neo4j)
    try:
        graph = NexusGraph()
        print("\n[ CAUSAL SYNAPSE RECALL ]")
        with graph.driver.session() as session:
            result = session.run("MATCH (a)-[r:CAUSES]->(b) RETURN a.name, b.name, r.confidence")
            records = list(result)
            if records:
                for record in records:
                    print(f"Verified Link: {record['a.name']} --(conf: {record['r.confidence']})--> {record['b.name']}")
            else:
                print("No causal links found in Neo4j.")
        graph.close()
    except Exception as e:
        print(f"Error recalling from Neo4j: {e}")

if __name__ == "__main__":
    test_recall()