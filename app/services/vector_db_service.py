import logging
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional

# Potentially load model name from config if it needs to be configurable
# For now, let's assume we use the same OpenAI model as in LLMService for consistency
# However, ChromaDB's embedding_functions.OpenAIEmbeddingFunction might have its own defaults
# or require specific setup if we don't pass embeddings directly.

# If we are generating embeddings with LLMService and passing them, we don't strictly need
# ChromaDB's OpenAIEmbeddingFunction here, but it's good to be aware of.

logger = logging.getLogger(__name__)

# Define a path for the persistent ChromaDB data
CHROMA_DATA_PATH = "./chroma_db_store"
DEFAULT_COLLECTION_NAME = "general_context"
PROPOSALS_COLLECTION_NAME = "proposals_content"  # New constant for proposals collection

class VectorDBService:
    def __init__(self, path: str = CHROMA_DATA_PATH):
        try:
            self.client = chromadb.PersistentClient(path=path)
            # We can also use chromadb.HttpClient(host='localhost', port=8000) if running a server
            logger.info(f"VectorDBService initialized with PersistentClient at path: {path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}", exc_info=True)
            self.client = None

    def _get_or_create_collection(self, collection_name: str = DEFAULT_COLLECTION_NAME):
        if not self.client:
            raise ConnectionError("ChromaDB client not initialized.")
        try:
            collection = self.client.get_or_create_collection(name=collection_name)
            logger.info(f"Accessed or created ChromaDB collection: {collection_name}")
            return collection
        except Exception as e:
            logger.error(f"Error getting or creating collection '{collection_name}': {e}", exc_info=True)
            raise

    async def store_embeddings(
        self,
        doc_id: int, # SQL Document ID
        text_chunks: List[str],
        embeddings: List[List[float]],
        chunk_metadatas: Optional[List[Dict[str, Any]]] = None, # e.g., {"document_sql_id": doc_id, "chunk_index": i}
        collection_name: str = DEFAULT_COLLECTION_NAME
    ) -> Optional[List[str]]:
        """
        Stores text chunks and their pre-computed embeddings in the specified ChromaDB collection.
        Each chunk is associated with the SQL document ID.
        Returns a list of ChromaDB IDs for the stored embeddings if successful, else None.
        """
        if not self.client:
            logger.error("VectorDBService client not initialized. Cannot store embeddings.")
            return None
        if len(text_chunks) != len(embeddings):
            logger.error("Number of text chunks and embeddings must be the same.")
            return None
        if chunk_metadatas and len(text_chunks) != len(chunk_metadatas):
            logger.error("Number of text chunks and chunk_metadatas must be the same if metadata is provided.")
            return None

        try:
            collection = self._get_or_create_collection(collection_name)
            
            ids_for_chroma = []
            final_metadatas = []

            for i, chunk in enumerate(text_chunks):
                chroma_id = f"doc_{doc_id}_chunk_{i}" # Create a unique ID for ChromaDB
                ids_for_chroma.append(chroma_id)
                
                metadata = {"document_sql_id": str(doc_id), "chunk_text_preview": chunk[:100]} # Basic metadata
                if chunk_metadatas and chunk_metadatas[i]:
                    metadata.update(chunk_metadatas[i]) # Merge with provided metadata
                final_metadatas.append(metadata)

            collection.add(
                embeddings=embeddings,
                documents=text_chunks, # Storing the text itself for potential retrieval
                metadatas=final_metadatas,
                ids=ids_for_chroma
            )
            logger.info(f"Successfully stored {len(text_chunks)} embeddings for document ID {doc_id} in collection '{collection_name}'. Chroma IDs: {ids_for_chroma}")
            return ids_for_chroma
        except Exception as e:
            logger.error(f"Error storing embeddings for document ID {doc_id}: {e}", exc_info=True)
            return None

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_n: int = 5,
        proposal_id_filter: Optional[int] = None, # To filter by proposal_id if linked in metadata
        collection_name: str = DEFAULT_COLLECTION_NAME
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Searches for text chunks in ChromaDB similar to the given query_embedding.
        Can optionally filter by proposal_id if documents are linked to proposals.
        Returns a list of search results, each containing metadata and distance, or None.
        """
        if not self.client:
            logger.error("VectorDBService client not initialized. Cannot search chunks.")
            return None

        try:
            collection = self._get_or_create_collection(collection_name)
            
            where_filter = None
            if proposal_id_filter is not None:
                # This assumes that the metadata for each chunk includes a 'proposal_id' field
                # when it's stored, and that it's stored as a string if we stored document_sql_id as string.
                # Let's assume we add a specific "proposal_id" field to metadata if filtering is needed.
                # For now, using document_sql_id as a proxy if documents are 1:1 with proposals for context.
                # A more robust way is to add `proposal_id` directly to metadata if available.
                # Let's assume `document_sql_id` can be used if `proposal_id_filter` maps to it.
                # Or we can introduce a specific metadata field like {"proposal_context_id": proposal_id_filter}
                # For Task 3.2, this is for general context; proposal_id filtering is for /ask <proposal_id>
                # So, let's assume metadata will have a "proposal_id": "<id>" field when relevant.
                where_filter = {"proposal_id": str(proposal_id_filter)}
                logger.info(f"Searching with filter: {where_filter}")
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_n,
                where=where_filter, # Apply filter if provided
                include=['metadatas', 'documents', 'distances'] # Specify what to include in results
            )
            
            # Results is a dict-like object, extract the relevant parts
            # Example structure of results for a single query_embedding:
            # {
            #   'ids': [['id1', 'id2']], 
            #   'distances': [[0.1, 0.2]], 
            #   'metadatas': [[meta1, meta2]], 
            #   'documents': [[doc1, doc2]]
            # }
            # We want to transform this into a list of dicts for easier use.
            
            search_hits = []
            if results and results.get('ids') and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    hit = {
                        "id": results['ids'][0][i],
                        "distance": results['distances'][0][i] if results.get('distances') else None,
                        "metadata": results['metadatas'][0][i] if results.get('metadatas') else None,
                        "document_content": results['documents'][0][i] if results.get('documents') else None,
                    }
                    search_hits.append(hit)
            
            logger.info(f"Found {len(search_hits)} similar chunks for query.")
            return search_hits
        except Exception as e:
            logger.error(f"Error searching for similar chunks: {e}", exc_info=True)
            return None

    async def get_document_chunks(
        self,
        sql_document_id: int,
        collection_name: str = DEFAULT_COLLECTION_NAME
    ) -> Optional[List[str]]:
        """
        Retrieves all text chunks from ChromaDB associated with a given SQL document ID.
        Returns a list of text chunks if successful, else None.
        """
        if not self.client:
            logger.error("VectorDBService client not initialized. Cannot retrieve chunks.")
            return None

        try:
            collection = self._get_or_create_collection(collection_name)
            
            # We stored document_sql_id as a string in metadata
            where_filter = {"document_sql_id": str(sql_document_id)}
            
            results = collection.get(
                where=where_filter,
                include=['documents'] # We only need the text content of the chunks
            )
            
            if results and results.get('documents'):
                logger.info(f"Successfully retrieved {len(results['documents'])} chunks for SQL document ID {sql_document_id} from collection '{collection_name}'.")
                return results['documents']
            else:
                logger.info(f"No chunks found for SQL document ID {sql_document_id} in collection '{collection_name}'.")
                return [] # Return empty list if no documents found, consistent with List[str] hint

        except Exception as e:
            logger.error(f"Error retrieving chunks for SQL document ID {sql_document_id}: {e}", exc_info=True)
            return None

    async def add_proposal_embedding(
        self, 
        proposal_id: int, 
        text_content: str, 
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        Adds or updates a proposal's embedding in the proposals_content collection.
        
        Args:
            proposal_id: The SQL ID of the proposal
            text_content: The text to be indexed (typically title + description)
            embedding: The pre-computed embedding vector for the text
            metadata: Additional metadata to store with the embedding, including:
                      - proposal_id: The SQL ID of the proposal
                      - status: The proposal status (e.g., "open", "closed")
                      - deadline_date_iso: ISO format of the deadline date
                      - creation_date_iso: ISO format of the creation date
                      - proposal_type: The type of proposal (e.g., "multiple_choice", "free_form")
                      - target_channel_id: The channel where the proposal is posted
                      
        Returns:
            The ChromaDB ID of the stored embedding if successful, else None
        """
        if not self.client:
            logger.error("VectorDBService client not initialized. Cannot store proposal embedding.")
            return None
        
        if not embedding:
            logger.error(f"No embedding provided for proposal ID {proposal_id}. Cannot store.")
            return None
            
        try:
            collection = self._get_or_create_collection(PROPOSALS_COLLECTION_NAME)
            
            # Create a unique ID for this proposal in ChromaDB
            chroma_id = f"proposal_{proposal_id}"
            
            # Ensure the required metadata is included
            # Convert numeric IDs to strings for ChromaDB compatibility
            metadata["proposal_id"] = str(proposal_id)
            
            # For updates, we use upsert (add or update if exists)
            collection.upsert(
                ids=[chroma_id],
                embeddings=[embedding],
                documents=[text_content],
                metadatas=[metadata]
            )
            
            logger.info(f"Successfully stored/updated embedding for proposal ID {proposal_id} in collection '{PROPOSALS_COLLECTION_NAME}'. Chroma ID: {chroma_id}")
            return chroma_id
        except Exception as e:
            logger.error(f"Error storing embedding for proposal ID {proposal_id}: {e}", exc_info=True)
            return None
            
    async def search_proposal_embeddings(
        self,
        query_embedding: List[float],
        top_n: int = 5,
        filter_proposal_ids: Optional[List[int]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Searches for proposals in ChromaDB similar to the given query_embedding.
        Can optionally filter by proposal_ids.
        
        Args:
            query_embedding: The embedding vector of the query
            top_n: Maximum number of results to return
            filter_proposal_ids: Optional list of proposal IDs to restrict the search to
            
        Returns:
            A list of search results, each containing metadata and distance, or None if error
        """
        if not self.client:
            logger.error("VectorDBService client not initialized. Cannot search proposal embeddings.")
            return None
            
        try:
            collection = self._get_or_create_collection(PROPOSALS_COLLECTION_NAME)
            
            where_filter = None
            if filter_proposal_ids is not None and len(filter_proposal_ids) > 0:
                # Convert numeric IDs to strings for ChromaDB compatibility
                filter_proposal_ids_str = [str(pid) for pid in filter_proposal_ids]
                where_filter = {"proposal_id": {"$in": filter_proposal_ids_str}}
                logger.info(f"Searching proposals with filter: {where_filter}")
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_n,
                where=where_filter,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Transform results into a list of dicts for easier use
            search_hits = []
            if results and results.get('ids') and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    hit = {
                        "id": results['ids'][0][i],
                        "distance": results['distances'][0][i] if results.get('distances') else None,
                        "metadata": results['metadatas'][0][i] if results.get('metadatas') else None,
                        "document_content": results['documents'][0][i] if results.get('documents') else None,
                    }
                    search_hits.append(hit)
            
            logger.info(f"Found {len(search_hits)} similar proposals for query.")
            return search_hits
        except Exception as e:
            logger.error(f"Error searching for similar proposals: {e}", exc_info=True)
            return None

# Example Usage (for testing - ensure LLMService is available for embeddings)
if __name__ == '__main__':
    import asyncio
    from app.services.llm_service import LLMService # For generating test embeddings

    async def test_vector_db_service():
        logging.basicConfig(level=logging.INFO)
        logger.info("Starting VectorDBService example...")

        # Ensure you have an OpenAI API Key for LLMService to generate embeddings
        llm_service = LLMService()
        if not llm_service.client:
            logger.error("LLMService could not be initialized. Cannot run VectorDBService example.")
            return

        vdb_service = VectorDBService(path="./test_chroma_db_store") # Use a test path
        if not vdb_service.client:
            logger.error("VectorDBService could not be initialized. Exiting example.")
            return

        # 1. Store some embeddings
        doc_id_1 = 101
        texts_1 = [
            "The sky is blue and the sun is bright.",
            "Apples are a type of fruit, often red or green.",
            "Software development requires careful planning and execution."
        ]
        embeddings_1 = []
        for text in texts_1:
            emb = await llm_service.generate_embedding(text)
            if emb:
                embeddings_1.append(emb)
            else:
                logger.error(f"Failed to generate embedding for: {text}")
                return
        
        # Example of adding metadata that includes proposal_id for some chunks
        metadatas_1 = [
            {"document_sql_id": str(doc_id_1), "chunk_index": 0, "topic": "weather"},
            {"document_sql_id": str(doc_id_1), "chunk_index": 1, "topic": "food", "proposal_id": "prop_A"},
            {"document_sql_id": str(doc_id_1), "chunk_index": 2, "topic": "work", "proposal_id": "prop_B"},
        ]

        if len(texts_1) == len(embeddings_1):
            stored_ids_1 = await vdb_service.store_embeddings(doc_id_1, texts_1, embeddings_1, chunk_metadatas=metadatas_1, collection_name="test_collection")
            if stored_ids_1:
                logger.info(f"Stored embeddings for doc {doc_id_1} with Chroma IDs: {stored_ids_1}")
            else:
                logger.error(f"Failed to store embeddings for doc {doc_id_1}.")
        else:
            logger.error("Mismatch in generated embeddings count for doc 1.")

        # 2. Search for similar chunks
        query_text = "Tell me about delicious red fruits."
        query_embedding = await llm_service.generate_embedding(query_text)

        if query_embedding:
            logger.info(f"Searching for chunks similar to: '{query_text}'")
            # Search without proposal filter
            search_results_all = await vdb_service.search_similar_chunks(query_embedding, top_n=2, collection_name="test_collection")
            if search_results_all is not None:
                logger.info(f"Search results (all, top 2): {search_results_all}")
            else:
                logger.error("Search (all) failed.")

            # Search with proposal filter (expecting the apple chunk)
            search_results_filtered = await vdb_service.search_similar_chunks(query_embedding, top_n=2, proposal_id_filter="prop_A", collection_name="test_collection")
            if search_results_filtered is not None:
                logger.info(f"Search results (filtered for proposal_id='prop_A', top 2): {search_results_filtered}")
            else:
                logger.error("Search (filtered) failed.")
        else:
            logger.error(f"Failed to generate query embedding for: '{query_text}'")
        
        # Clean up the test collection/directory if needed, or re-run for idempotency checks
        # For example, you could delete the collection or the directory:
        # try:
        #     vdb_service.client.delete_collection("test_collection")
        #     logger.info("Cleaned up test_collection.")
        # except Exception as e:
        #     logger.warning(f"Could not delete test_collection: {e}")
        # import shutil
        # shutil.rmtree("./test_chroma_db_store")
        # logger.info("Cleaned up ./test_chroma_db_store directory.")

    asyncio.run(test_vector_db_service()) 