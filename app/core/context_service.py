import logging
import hashlib
from typing import Optional, List, Dict, Any, Tuple
import httpx # For fetching content from URLs

from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.persistence.repositories.document_repository import DocumentRepository
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.text_processing import simple_chunk_text # Moved import
from app.persistence.models.proposal_model import Proposal
from app.persistence.models.document_model import Document
from app.persistence.repositories.proposal_repository import ProposalRepository

logger = logging.getLogger(__name__)

class ContextService:
    def __init__(
        self,
        db_session: AsyncSession,
        llm_service: LLMService,
        vector_db_service: VectorDBService
    ):
        self.db_session = db_session
        self.llm_service = llm_service
        self.vector_db_service = vector_db_service
        self.document_repository = DocumentRepository(db_session)

    async def _fetch_content_from_url(self, url: str) -> Optional[str]:
        """Fetches text content from a URL."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0) # 10 second timeout
                response.raise_for_status() # Raise an exception for HTTP 4xx/5xx errors
                # For simplicity, assuming text content. Could add content-type checks.
                # Basic HTML stripping might be needed for web pages, or use a library like BeautifulSoup.
                # For now, returning raw text content.
                # TODO: Add better HTML parsing or content extraction (e.g. using a library like `trafilatura` or `beautifulsoup4`)
                return response.text
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching URL {url}: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching URL {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching URL {url}: {e}", exc_info=True)
            return None

    async def process_and_store_document(
        self,
        content_source: str, # Can be raw text or a URL
        source_type: str, # e.g., "user_text", "user_url", "admin_upload_text", "admin_upload_url"
        title: Optional[str] = None,
        proposal_id: Optional[int] = None,
        chunk_size: int = 1000, # Default chunk size for text processing
        chunk_overlap: int = 100 # Default overlap for text processing
    ) -> Optional[int]: # Returns the SQL Document ID if successful
        """
        Processes content (text or URL), chunks it, generates embeddings, 
        and stores it in the database and vector store.
        """
        logger.info(f"Processing document. Title: '{title}', Source Type: '{source_type}', Proposal ID: {proposal_id}")

        text_content: Optional[str] = None
        final_source_url: Optional[str] = None

        if source_type.endswith("_url"):
            final_source_url = content_source
            text_content = await self._fetch_content_from_url(content_source)
            if not text_content:
                logger.error(f"Failed to fetch content from URL: {content_source}")
                return None
            if not title:
                 # Basic title from URL if not provided
                title = content_source.split('/')[-1] or content_source
        elif source_type.endswith("_text"):
            text_content = content_source
        else:
            logger.error(f"Invalid source_type: {source_type}")
            return None
        
        if not text_content:
            logger.warning("No text content to process.")
            return None

        content_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()

        # TODO: Check if content_hash already exists in DocumentRepository to avoid duplicates?
        # This would require a method in DocumentRepository like `get_document_by_hash`.
        # For now, we proceed with adding it.

        # 1. Chunk the text
        # Using the simple_chunk_text defined above for now.
        text_chunks = simple_chunk_text(text_content, chunk_size=chunk_size, overlap=chunk_overlap)
        if not text_chunks:
            logger.warning("Text content resulted in no chunks.")
            return None
        logger.info(f"Text content split into {len(text_chunks)} chunks.")

        # 2. Generate embeddings for chunks via LLMService
        embeddings: List[List[float]] = []
        for i, chunk in enumerate(text_chunks):
            try:
                embedding = await self.llm_service.generate_embedding(chunk)
                if embedding:
                    embeddings.append(embedding)
                else:
                    logger.error(f"Failed to generate embedding for chunk {i} of document '{title}'. Skipping document.")
                    return None # Or handle partial failure differently
            except Exception as e:
                logger.error(f"Error generating embedding for chunk {i} of document '{title}': {e}", exc_info=True)
                return None
        
        if len(embeddings) != len(text_chunks):
            logger.error("Mismatch between number of chunks and generated embeddings. Aborting storage.")
            return None

        # 3. Store document metadata in DocumentRepository (SQL DB)
        try:
            # The vector_ids will be stored after successful storage in VectorDB
            # So, initially, vector_ids might be None or empty in the SQL record
            # Or, we store in VectorDB first, get IDs, then save to SQL. Let's try the latter.
            pass # DB storage will happen after vector storage
        except Exception as e:
            logger.error(f"Error preparing to store document metadata for '{title}': {e}", exc_info=True)
            # await self.db_session.rollback() # Handled by service/handler level ideally
            return None

        # 4. Store embeddings in VectorDBService
        # We need the SQL document ID first to link embeddings. This is a bit circular.
        # Option A: Store Document in SQL -> Get ID -> Store in VectorDB with SQL ID -> Update Document with Vector IDs.
        # Option B: Decide on a temporary ID strategy if needed, or make SQL Document ID nullable in Chroma metadata initially.

        # Let's try Option A: Store in SQL (without vector_ids), get ID, then store in Chroma, then update SQL with Chroma IDs.
        # This requires Document.vector_ids to be nullable or updatable.

        sql_document = await self.document_repository.add_document(
            title=title,
            content_hash=content_hash,
            source_url=final_source_url,
            vector_ids=None, # Will update this later
            proposal_id=proposal_id,
            raw_content=text_content # Storing the raw/cleaned text content
        )
        if not sql_document or not sql_document.id:
            logger.error(f"Failed to store document metadata in SQL DB for title '{title}'.")
            # await self.db_session.rollback()
            return None
        
        logger.info(f"Stored document metadata in SQL with ID: {sql_document.id} for title: '{title}'")

        # Now store in VectorDB using sql_document.id
        chunk_metadatas = [
            {"document_sql_id": str(sql_document.id), "chunk_index": i, "original_source": final_source_url or source_type}
            for i in range(len(text_chunks))
        ]
        
        chroma_vector_ids = await self.vector_db_service.store_embeddings(
            doc_id=sql_document.id,
            text_chunks=text_chunks,
            embeddings=embeddings,
            chunk_metadatas=chunk_metadatas
        )

        if not chroma_vector_ids:
            logger.error(f"Failed to store embeddings in VectorDB for SQL document ID {sql_document.id}. Document metadata in SQL DB was still created.")
            # Here, we might want to decide on a cleanup strategy for the SQL entry if vector storage fails.
            # For now, we proceed, but the document won't be searchable via vectors.
            # Update vector_ids to empty list or similar to indicate failure for this part.
            sql_document.vector_ids = [] # Indicate no vectors stored or failure
        else:
            logger.info(f"Successfully stored {len(chroma_vector_ids)} embeddings in VectorDB for SQL document ID {sql_document.id}")
            sql_document.vector_ids = chroma_vector_ids

        # Update the SQL document with the Chroma vector IDs
        try:
            await self.db_session.commit() # Commits the update to sql_document.vector_ids
            await self.db_session.refresh(sql_document)
            logger.info(f"Successfully updated SQL document ID {sql_document.id} with Chroma vector IDs: {sql_document.vector_ids}")
            return sql_document.id
        except Exception as e:
            logger.error(f"Error committing vector_ids to SQL document ID {sql_document.id}: {e}", exc_info=True)
            # await self.db_session.rollback()
            # SQL doc was created, vectors possibly stored, but link in SQL failed. Potential inconsistency.
            return None # Or return sql_document.id but log the linking failure more severely

    async def get_document_content(self, document_id: int) -> Optional[str]:
        """Fetches the raw content of a document by its ID."""
        document = await self.document_repository.get_document_by_id(document_id)
        if document and document.raw_content:
            return document.raw_content
        elif document:
            logger.warning(f"Document ID {document_id} found, but it has no raw_content.")
            return None
        else:
            logger.warning(f"Document ID {document_id} not found.")
            return None

    async def list_documents_for_proposal(self, proposal_id: int) -> List[Document]:
        """Lists all documents associated with a given proposal_id."""
        return await self.document_repository.get_documents_by_proposal_id(proposal_id)

    async def get_answer_for_question(self, question_text: str, proposal_id_filter: Optional[int] = None, top_n_chunks: int = 3) -> str:
        """
        Answers a question using RAG by fetching relevant document chunks.
        """
        logger.info(f"Getting answer for question: '{question_text}', proposal_id_filter: {proposal_id_filter}")

        try:
            query_embedding = await self.llm_service.generate_embedding(question_text)
            if not query_embedding:
                logger.warning("Failed to generate embedding for question.")
                return "I couldn't process your question at the moment. Please try again later."

            # Assuming search_similar_chunks returns a list of dicts like:
            # [{'text_chunk': str, 'sql_document_id': int, 'score': float, 'metadata': {'title': 'Doc Title'}}]
            # Or that metadata contains enough to fetch the title.
            # The VectorDBService.search_similar_chunks might need to be adjusted or its return type confirmed.
            # For now, we'll assume it returns the chunk text and some document metadata.
            
            # The task mentions: search_similar_chunks(query_embedding, proposal_id_filter, top_n)
            # Let's assume it returns a list of dicts, each having 'text' and 'metadata' (which includes 'sql_document_id' and 'title')
            similar_chunks_results = await self.vector_db_service.search_similar_chunks(
                query_embedding=query_embedding,
                proposal_id_filter=proposal_id_filter,
                top_n=top_n_chunks
            )

            if not similar_chunks_results:
                logger.info("No similar document chunks found for the question.")
                # Try a general search if proposal_id_filter was used and nothing found
                if proposal_id_filter is not None:
                    logger.info(f"Retrying search without proposal_id_filter for question: '{question_text}'")
                    similar_chunks_results = await self.vector_db_service.search_similar_chunks(
                        query_embedding=query_embedding,
                        proposal_id_filter=None, # Search global docs too
                        top_n=top_n_chunks
                    )
                    if not similar_chunks_results:
                         return "I couldn't find any relevant information for your question."
                else:
                    return "I couldn't find any relevant information for your question."
            
            context_str = ""
            sources_cited = set() # To avoid duplicate source citations
            source_details_for_prompt = []

            for chunk_info in similar_chunks_results:
                # Assuming chunk_info is a dict with 'text_content' and 'metadata'
                # And metadata contains 'sql_document_id' and 'title' (document title)
                text_chunk = chunk_info.get('text_content', '') # Prefer 'text_content' if available from vector DB
                metadata = chunk_info.get('metadata', {})
                doc_id = metadata.get('sql_document_id')
                doc_title = metadata.get('title', f"Document ID {doc_id}" if doc_id else "a relevant document")

                if text_chunk:
                    context_str += f"- {text_chunk}\\n"
                    source_details_for_prompt.append(f"Content from '{doc_title}' (ID: {doc_id})")
                    sources_cited.add(f"'{doc_title}' (ID: {doc_id})")

            if not context_str:
                 logger.info("No text content found in similar chunks.")
                 return "I found some documents that might be related, but I couldn't extract specific text to answer your question."

            prompt = (
                f"You are a helpful assistant. Based on the following context, please answer the user's question.\\n"
                f"Context from documents ({', '.join(sources_cited)}):\\n{context_str}\\n"
                f"User's Question: {question_text}\\n\\n"
                f"Answer directly. If the context does not provide a sufficient answer, please state that you don't have enough information from the provided context."
            )
            
            logger.debug(f"Prompt for /ask command:\\n{prompt}")

            answer = await self.llm_service.get_completion(prompt)

            # Append source citation to the answer
            if sources_cited:
                answer += f"\\n\\nSources: {', '.join(list(sources_cited))}."
            
            return answer

        except Exception as e:
            logger.error(f"Error getting answer for question: {e}", exc_info=True)
            return "Sorry, I encountered an error while trying to answer your question. Please try again later."
 