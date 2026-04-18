import os
import time
from typing import List, Dict, Any

try:
    from chromadb import Client
    from chromadb.config import Settings
    from chromadb.errors import InvalidDimensionException
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    Client = None
    Settings = None
    InvalidDimensionException = None

if CHROMADB_AVAILABLE:
    # Initialize ChromaDB client
    CHROMA_HOST = os.getenv('CHROMA_HOST', 'localhost')
    CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
    CHROMA_SETTINGS = Settings(
        chroma_server_host=CHROMA_HOST,
        chroma_server_http_port=CHROMA_PORT,
        anonymized_telemetry=False
    )

    # ChromaDB client
    client = Client(CHROMA_SETTINGS)

    # Collection for agent memory
    memory_collection = client.get_or_create_collection(
        name="agent_memory",
        metadata={"hnsw:space": "cosine"}
    )
else:
    client = None
    memory_collection = None


def store_memory(embedding: List[float], metadata: Dict[str, Any], timestamp: float = None) -> str:
    """
    Store a memory item in the vector database.
    """
    if not CHROMADB_AVAILABLE:
        raise ImportError("chromadb not installed. Run: pip install chromadb")
    
    if timestamp is None:
        timestamp = time.time()
    
    # Create metadata with timestamp
    full_metadata = {
        "timestamp": timestamp,
        "created_at": time.ctime(timestamp),
        **metadata
    }
    
    # Store in ChromaDB
    memory_id = memory_collection.add(
        embeddings=[embedding],
        metadatas=[full_metadata],
        ids=[str(int(timestamp))]
    )
    
    return str(int(timestamp))


def search_memory(query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search for similar memories using similarity search.
    """
    if not CHROMADB_AVAILABLE:
        return []
    
    try:
        results = memory_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["metadatas", "distances"]
        )
        
        return [
            {
                "id": id,
                "metadata": metadata,
                "distance": distance
            }
            for id, metadata, distance in zip(
                results["ids"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    except InvalidDimensionException:
        # Handle dimension mismatch
        return []


def delete_memory(memory_id: str) -> bool:
    """
    Delete a memory item by ID.
    """
    if not CHROMADB_AVAILABLE:
        return False
    
    try:
        memory_collection.delete(ids=[memory_id])
        return True
    except Exception:
        return False


def get_memory_stats() -> Dict[str, Any]:
    """
    Get statistics about the memory collection.
    """
    if not CHROMADB_AVAILABLE:
        return {"count": 0, "collection_name": "agent_memory"}
    
    try:
        return {
            "count": memory_collection.count(),
            "collection_name": memory_collection.name
        }
    except Exception:
        return {"count": 0, "collection_name": "agent_memory"}


def get_all_memory() -> List[Dict[str, Any]]:
    """
    Retrieve all memory items for debugging purposes.
    """
    if not CHROMADB_AVAILABLE:
        return []
    
    try:
        results = memory_collection.get(include=["metadatas"])
        return [
            {
                "id": id,
                "metadata": metadata
            }
            for id, metadata in zip(results["ids"], results["metadatas"])
        ]
    except Exception:
        return []
