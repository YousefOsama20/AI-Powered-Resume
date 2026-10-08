"""
VectorDBController
──────────────────
Handles interaction with ChromaDB to persist, query, and delete resume chunks.
"""

import os
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from .BaseController import BaseController
from models.enums.ResumeSectionEnum import ResumeSectionEnum

# Canonical ChromaDB collection names. All candidate-CV reads/writes must use
# CANDIDATE_COLLECTION so indexing and matching never drift apart again.
# (NOTE: settings.VECTOR_DB_COLLECTION / default_collection is legacy and
# must NOT be relied on for the candidate pool.)
CANDIDATE_COLLECTION = "candidates"


class VectorDBController(BaseController):

    def __init__(self):
        # Type: Sub-function
        super().__init__()
        
        # Ensure DB path exists
        os.makedirs(self.app_settings.VECTOR_DB_PATH, exist_ok=True)
        
        # Initialize persistent ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=self.app_settings.VECTOR_DB_PATH,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # We use a default collection name unless overridden
        self.default_collection = self.app_settings.VECTOR_DB_COLLECTION
        
    def _get_collection(self, collection_name: str = None):
        # Get or create a ChromaDB collection. | Internal
        # Type: Sub-function
        """Helper to get or create a collection."""
        name = collection_name or self.default_collection
        # In this project, we provide our own embeddings, so we don't strictly need 
        # Chroma's default embedding function, but we can just let it default 
        # or pass None if we only supply embeddings directly.
        return self.chroma_client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"} # Use cosine similarity
        )

    def index_chunks(self, 
                     chunks: List[Any], # List of Langchain Documents
                     embeddings: List[List[float]],
                     collection_name: str = None) -> bool:
        # Type: Main function
        """
        Upsert document chunks and their embeddings into ChromaDB.
        Uses upsert, so re-indexing the same chunk_id will overwrite.
        """
        try:
            collection = self._get_collection(collection_name)
            
            ids = [chunk.metadata.get("chunk_id") for chunk in chunks]
            documents = [chunk.page_content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]

            # Upsert in batches of 100 for safety (though Chroma can handle more)
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                collection.upsert(
                    ids=ids[i:i+batch_size],
                    embeddings=embeddings[i:i+batch_size],
                    documents=documents[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size]
                )
            return True
        except Exception as e:
            print(f"Error indexing to VectorDB: {e}")
            return False

    def search(self, query_embedding: List[float], customer_id: str = None, n_results: int = 5,
                    section_filter: str = None, collection_name: str = None) -> List[Dict[str, Any]]:
        # Type: Main function
        """
        Perform a similarity search across the global candidate pool.
        Optionally filter by a specific customer_id or resume section.
        """
        try:
            collection = self._get_collection(collection_name)
            
            where_clause = {}
            conditions = []
            
            if customer_id:
                conditions.append({"customer_id": customer_id})
                
            if section_filter and section_filter in [e.value for e in ResumeSectionEnum]:
                conditions.append({"section": section_filter})
                
            if len(conditions) == 1:
                where_clause = conditions[0]
            elif len(conditions) > 1:
                where_clause = {"$and": conditions}
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format the output
            formatted_results = []
            if results["ids"] and len(results["ids"]) > 0 and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                        "score": 1 - results["distances"][0][i] # roughly convert distance to similarity score
                    })
                    
            return formatted_results
        except Exception as e:
            print(f"Error searching VectorDB: {e}")
            return []

    def delete_by_file(self, customer_id: str, file_id: str, collection_name: str = None) -> bool:
        # Delete all vectors for a specific file_id. | Customer (CV deletion)
        # Type: Main function
        """Deletes all chunks associated with a specific file for a customer."""
        try:
            collection = self._get_collection(collection_name)
            
            where_clause = {
                "$and": [
                    {"customer_id": customer_id},
                    {"file_id": file_id}
                ]
            }
            
            # Chroma deletes matching metadatas
            collection.delete(where=where_clause)
            return True
        except Exception as e:
            print(f"Error deleting file from VectorDB: {e}")
            return False

    def delete_by_customer(self, customer_id: str, collection_name: str = None) -> bool:
        # Delete all vectors for a customer. | Customer (account cleanup)
        # Type: Main function
        """Deletes all chunks associated with a specific customer."""
        try:
            collection = self._get_collection(collection_name)
            collection.delete(where={"customer_id": customer_id})
            return True
        except Exception as e:
            print(f"Error deleting customer from VectorDB: {e}")
            return False

    def get_collection_count(self, collection_name: str = None) -> int:
        # Get total number of vectors in a collection. | Internal
        # Type: Main function
        """Returns total items in the collection."""
        try:
            collection = self._get_collection(collection_name)
            return collection.count()
        except:
            return 0

    def get_all_indexed_files(self, collection_name: str = None) -> List[Dict[str, str]]:
        # List all unique file_ids indexed in a collection. | Internal
        # Type: Main function
        """Returns a list of all unique customer_id and file_id combinations in the DB."""
        try:
            collection = self._get_collection(collection_name)
            
            # Fetch all metadata
            results = collection.get(include=["metadatas"])
            
            unique_files = set()
            for meta in results.get("metadatas", []):
                if meta:
                    customer_id = meta.get("customer_id")
                    file_id = meta.get("file_id")
                    if customer_id and file_id:
                        unique_files.add((customer_id, file_id))
                    
            return [{"customer_id": c_id, "file_id": f_id} for c_id, f_id in unique_files]
        except Exception as e:
            print(f"Error fetching files from VectorDB: {e}")
            return []
