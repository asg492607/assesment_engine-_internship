import os
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

def get_qdrant_client():
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=2.0)
        return client
    except Exception:
        return None

def store_candidate_vector(candidate_id: str, scores: dict, role_title: str):
    """
    Layer 7: Vector database indexing.
    Converts candidate scores into a normalized assessment embedding and upserts it into Qdrant.
    """
    client = get_qdrant_client()
    if not client:
        print("Qdrant offline or unreachable. Skipping vector embedding storage.")
        return False
        
    collection_name = "candidate_profiles"
    try:
        # Ensure collection exists
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        
        if not exists:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=8, distance=Distance.COSINE),
            )
            
        # Create a simple mock embedding vector representing the candidate's scores:
        # Knowledge, Solving, Creativity, Communication, Reasoning, Execution, Career Readiness, Company Match
        vector = [
            scores.get("Knowledge", 75) / 100.0,
            scores.get("Problem Solving", 75) / 100.0,
            scores.get("Creativity", 75) / 100.0,
            scores.get("Communication", 75) / 100.0,
            scores.get("Reasoning", 75) / 100.0,
            scores.get("Execution", 75) / 100.0,
            scores.get("Career Readiness", 75) / 100.0,
            scores.get("Company Match", 75) / 100.0,
        ]
        
        client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=hash(candidate_id) % 10000000, # convert string to integer id
                    vector=vector,
                    payload={
                        "candidate_id": candidate_id,
                        "role_title": role_title,
                        "scores": scores
                    }
                )
            ]
        )
        print(f"Successfully upserted candidate {candidate_id} vector embedding to Qdrant.")
        return True
    except Exception as e:
        print(f"Error during Qdrant operations: {str(e)}")
        return False
