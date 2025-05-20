import logging
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone # Import timedelta for date range parsing
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig # For fetching and parsing URLs
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.persistence.repositories.document_repository import DocumentRepository
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.text_processing import simple_chunk_text # Moved import
from app.persistence.models.proposal_model import Proposal
from app.persistence.models.document_model import Document
from app.persistence.repositories.proposal_repository import ProposalRepository
from app.services.vector_db_service import DEFAULT_COLLECTION_NAME

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
        """Fetches text content from a URL using Crawl4AI."""
        try:
            # Configure Crawl4AI for a simple run
            browser_config = BrowserConfig(
                headless=True,
                java_script_enabled=True # Explicitly enable JavaScript
            )
            # Using a markdown generator with a pruning filter as per crawl4ai docs for potentially better content extraction
            md_generator = DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(threshold=0.4, threshold_type="fixed") # Default values from docs
            )
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,  # To get fresh content
                markdown_generator=md_generator,
                wait_until="networkidle"  # Wait for network activity to cease
            )
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
            
            if result.success and result.markdown:
                # Try fit_markdown first, then raw_markdown as a fallback
                content_to_return = result.markdown.fit_markdown
                source_of_content = "fit_markdown"
                # Check if fit_markdown is None or empty/minimal before trying len()
                if content_to_return is None or len(content_to_return.strip()) <= 1:
                    logger.info(f"fit_markdown for {url} was empty or minimal (Content: '{content_to_return}'). Falling back to raw_markdown.")
                    content_to_return = result.markdown.raw_markdown
                    source_of_content = "raw_markdown"
                    # Check raw_markdown as well
                    if content_to_return is None or len(content_to_return.strip()) <=1:
                        logger.warning(f"Both fit_markdown and raw_markdown for {url} are None or empty/minimal. Content: '{content_to_return}'")
                        # content_to_return remains None or empty here which is handled by the next block

                # Only log length if content_to_return is not None
                if content_to_return is not None:
                    logger.info(f"Successfully fetched and processed URL {url} with Crawl4AI using {source_of_content}. Markdown length: {len(content_to_return)}")
                    logger.info(f"Crawl4AI {source_of_content} content (first 100 chars): '{content_to_return[:100]}'")
                else:
                    # This case implies both fit_markdown and raw_markdown were None or empty
                    logger.warning(f"Crawl4AI fetched URL {url} successfully, but no usable markdown content was generated from fit_markdown or raw_markdown.")
                return content_to_return # This can be None if both are None/empty
            elif not result.success:
                logger.error(f"Crawl4AI failed to fetch URL {url}. Error: {result.error_message}")
                return None
            else: # result.success but no markdown (should be rare for valid HTML pages)
                logger.warning(f"Crawl4AI fetched URL {url} successfully, but no markdown content was generated.")
                return None
        except Exception as e:
            logger.error(f"Unexpected error fetching URL {url} with Crawl4AI: {e}", exc_info=True)
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
        # Prepare base metadata for each chunk
        base_metadata_for_chunks = {
            "document_sql_id": str(sql_document.id),
            "original_source": final_source_url or source_type,
            "title": title # The original title passed or derived
        }
        if proposal_id:
            base_metadata_for_chunks["proposal_id"] = str(proposal_id) # Add proposal_id if available

        chunk_metadatas = []
        for i in range(len(text_chunks)):
            meta = base_metadata_for_chunks.copy()
            meta["chunk_index"] = i
            # The chunk_text_preview is added by VectorDBService itself, no need to add it here.
            # We are passing the original title to the vector store metadata.
            # The dynamic title for proposals will be constructed during retrieval in get_answer_for_question.
            chunk_metadatas.append(meta)
        
        logger.info(f"ContextService: About to store embeddings for SQL document ID {sql_document.id}. Chunk metadatas being passed: {chunk_metadatas}")

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

    async def _get_raw_document_context_for_query(self, question_text: str, proposal_id_filter: Optional[int] = None, top_n_chunks: int = 3) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Fetches relevant raw document chunks and their sources for a given question.
        Returns a tuple: (formatted_context_string, list_of_source_details_dicts).
        Each dict in list_of_source_details_dicts is like: {"id": 123, "title": "Document Title"}
        """
        logger.info(f"_get_raw_document_context_for_query: question='{question_text}', proposal_id_filter={proposal_id_filter}")
        query_embedding = await self.llm_service.generate_embedding(question_text)
        if not query_embedding:
            logger.warning("_get_raw_document_context_for_query: Failed to generate embedding for question.")
            return "", [] # Return empty context and sources

        similar_chunks_results = await self.vector_db_service.search_similar_chunks(
            query_embedding=query_embedding,
            proposal_id_filter=proposal_id_filter,
            top_n=top_n_chunks
        )

        if not similar_chunks_results:
            logger.info("_get_raw_document_context_for_query: No similar document chunks found.")
            # If a filter was applied, don't retry here; let the caller decide on broader searches.
            return "", []
        
        context_str_parts = []
        source_details_list: List[Dict[str, Any]] = [] # New: list of dicts

        for chunk_info in similar_chunks_results:
            text_chunk = chunk_info.get('document_content', '')
            metadata = chunk_info.get('metadata', {})
            doc_id_str = metadata.get('document_sql_id') # Changed variable name to avoid conflict
            chunk_preview = metadata.get('chunk_text_preview', '')
            actual_title = metadata.get('title')
            linked_proposal_id = metadata.get('proposal_id')

            doc_title_display: str
            if linked_proposal_id:
                preview_text = chunk_preview if chunk_preview else text_chunk
                doc_title_display = f"Proposal {linked_proposal_id} context: {preview_text[:30]}..."
            elif actual_title:
                doc_title_display = actual_title
            elif chunk_preview:
                doc_title_display = f"Preview: {chunk_preview[:30]}..."
            elif doc_id_str: # Check doc_id_str before defaulting to "Unknown document"
                doc_title_display = f"Document ID {doc_id_str}"
            else:
                doc_title_display = "Unknown document"

            if text_chunk:
                context_str_parts.append(f"- {text_chunk}") # Store raw chunk
                if doc_id_str: # Only add to sources if there's a doc_id to link to
                    try:
                        doc_id_int = int(doc_id_str) # Ensure it's an int for the /view_doc command
                        # Add to list of source details for buttons
                        # To avoid duplicates for buttons if multiple chunks from same doc,
                        # this could be turned into a set of tuples (id, title) then converted back,
                        # or handled by the caller. For now, allow duplicates, caller can refine.
                        source_details_list.append({"id": doc_id_int, "title": doc_title_display})
                    except ValueError:
                        logger.warning(f"_get_raw_document_context_for_query: Could not parse doc_id '{doc_id_str}' to int for source button.")
        
        if not context_str_parts:
            logger.info("_get_raw_document_context_for_query: No text content found in similar chunks.")
            return "", []
        
        # Construct the full context string
        # We don't add "Context from documents..." here, the caller can do that if needed.
        full_context_str = "\n".join(context_str_parts)
        # Deduplicate source_details_list based on 'id' before returning to avoid redundant buttons for the same document.
        # Title might vary slightly if it's chunk-derived, so prioritize ID for uniqueness.
        unique_source_details = []
        seen_doc_ids = set()
        for detail in source_details_list:
            if detail['id'] not in seen_doc_ids:
                unique_source_details.append(detail)
                seen_doc_ids.add(detail['id'])
        
        return full_context_str, unique_source_details

    async def get_answer_for_question(self, question_text: str, proposal_id_filter: Optional[int] = None, top_n_chunks: int = 3) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Answers a question using RAG by fetching relevant document chunks and synthesizing an answer.
        Returns a tuple: (answer_string, list_of_source_details_for_buttons)
        """
        logger.info(f"get_answer_for_question: question='{question_text}', proposal_id_filter={proposal_id_filter}")

        try:
            raw_context, source_details = await self._get_raw_document_context_for_query(
                question_text=question_text,
                proposal_id_filter=proposal_id_filter,
                top_n_chunks=top_n_chunks
            )

            if not raw_context:
                # If initial search (e.g., with proposal_id_filter) found nothing, try a broader search only if a filter was active.
                if proposal_id_filter is not None:
                    logger.info(f"get_answer_for_question: No context found with proposal_id_filter {proposal_id_filter}. Retrying without filter.")
                    raw_context, source_details = await self._get_raw_document_context_for_query(
                        question_text=question_text,
                        proposal_id_filter=None, # Broader search
                        top_n_chunks=top_n_chunks
                    )
                    if not raw_context:
                        return "I couldn't find any relevant information for your question even after a broader search.", []
                else:
                    return "I couldn't find any relevant information for your question.", []
            
            # Now, raw_context contains the chunks and source_details has the structured source info.
            # We need to format the prompt for the LLM.
            context_header = ""
            # Create display names from source_details for the prompt
            source_display_names_for_prompt = []
            if source_details:
                for detail in source_details:
                    display_name = f"'{detail['title']}'"
                    if 'id' in detail: # Should always be there if it's a valid source for a button
                        display_name += f" (Doc ID: {detail['id']})"
                    source_display_names_for_prompt.append(display_name)

            if source_display_names_for_prompt:
                context_header = f"Context from documents ({', '.join(source_display_names_for_prompt)}):\n"
            
            prompt = (
                f"You are a helpful assistant. Based on the following context, please answer the user's question.\n"
                f"{context_header}{raw_context}\n"
                f"User's Question: {question_text}\n\n"
                f"Answer directly. If the context does not provide a sufficient answer, please state that you don't have enough information from the provided context."
            )
            
            logger.info(f"get_answer_for_question: Prompt for LLM:\n{context_header}{raw_context}")

            answer = await self.llm_service.get_completion(prompt)

            return answer, source_details # Return the answer and the structured source details

        except Exception as e:
            logger.error(f"Error getting answer for question '{question_text}': {e}", exc_info=True)
            return "Sorry, I encountered an error while trying to answer your question. Please try again later.", []

    async def _parse_date_query_to_range(self, date_query: Optional[str]) -> Optional[Tuple[Optional[datetime], Optional[datetime]]]:
        """
        Parses a natural language date query into a start and end datetime tuple using LLMService.
        """
        if not date_query:
            logger.debug("_parse_date_query_to_range called with no date_query.")
            return None

        parsed_range_dict = await self.llm_service.parse_natural_language_date_range_query(date_query)

        if not parsed_range_dict:
            logger.warning(f"LLMService.parse_natural_language_date_range_query returned None for query: '{date_query}'.")
            return None

        start_datetime_str = parsed_range_dict.get("start_datetime")
        end_datetime_str = parsed_range_dict.get("end_datetime")

        start_datetime: Optional[datetime] = None
        end_datetime: Optional[datetime] = None

        try:
            if start_datetime_str:
                # LLMService should return it in "YYYY-MM-DD HH:MM:SS UTC" format
                start_datetime = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M:%S %Z")
                # Ensure it's timezone-aware and UTC
                if start_datetime.tzinfo is None:
                    start_datetime = start_datetime.replace(tzinfo=timezone.utc)
                else:
                    start_datetime = start_datetime.astimezone(timezone.utc)
            
            if end_datetime_str:
                end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M:%S %Z")
                if end_datetime.tzinfo is None:
                    end_datetime = end_datetime.replace(tzinfo=timezone.utc)
                else:
                    end_datetime = end_datetime.astimezone(timezone.utc)
            
            if start_datetime or end_datetime:
                logger.info(f"Successfully parsed date query '{date_query}' into range: Start={start_datetime}, End={end_datetime}")
                return (start_datetime, end_datetime)
            else:
                logger.warning(f"Date query '{date_query}' resulted in no valid start or end datetimes after LLM parsing.")
                return None
                
        except ValueError as ve:
            logger.error(f"Error parsing datetime strings from LLM for date_query '{date_query}'. Start: '{start_datetime_str}', End: '{end_datetime_str}'. Error: {ve}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error in _parse_date_query_to_range for '{date_query}': {e}", exc_info=True)
            return None

    async def handle_intelligent_ask(self, query_text: str, user_telegram_id: int) -> Tuple[str, List[Dict[str, Any]]]:
        logger.info(f"Handling intelligent ask from user {user_telegram_id}: '{query_text}'")
        
        analysis = await self.llm_service.analyze_ask_query(query_text)
        if analysis.get("error"):
            logger.error(f"Error analyzing ask query: {analysis.get('error')}")
            return "Sorry, I had trouble understanding your question. Please try rephrasing.", []

        intent = analysis.get("intent", "query_general_docs")
        logger.info(f"Determined intent: {intent}")

        if intent == "query_proposals":
            content_keywords = analysis.get("content_keywords")
            structured_filters = analysis.get("structured_filters", {})
            
            status_filter = structured_filters.get("status")
            type_filter = structured_filters.get("proposal_type")
            date_query_filter = structured_filters.get("date_query")

            # Initialize ProposalRepository
            proposal_repo = ProposalRepository(self.db_session)

            # Parse date_query into a date range
            # This is a simplified date parsing. For production, this would need to be more robust.
            deadline_range = await self._parse_date_query_to_range(date_query_filter)
            
            # 1. Get proposals based on structured filters (SQL query)
            candidate_proposals_sql: List[Proposal] = []
            if status_filter or type_filter or deadline_range:
                # Check if this is a creation date query or deadline date query
                date_query_type = analysis.get("date_query_type", "deadline")
                logger.info(f"Date query type for '{date_query_filter}': {date_query_type}")
                
                # Apply the date range to the appropriate parameter based on the query type
                if date_query_type == "creation" and deadline_range:
                    logger.info(f"Applying date range {deadline_range} to creation_date_range parameter")
                    candidate_proposals_sql = await proposal_repo.find_proposals_by_dynamic_criteria(
                        status=status_filter,
                        proposal_type=type_filter,
                        creation_date_range=deadline_range  # Use creation_date_range for "creation" date queries
                    )
                else:
                    logger.info(f"Applying date range {deadline_range} to deadline_date_range parameter")
                    candidate_proposals_sql = await proposal_repo.find_proposals_by_dynamic_criteria(
                        status=status_filter,
                        proposal_type=type_filter,
                        deadline_date_range=deadline_range  # Use deadline_date_range for "deadline" date queries (default)
                    )
                logger.info(f"Found {len(candidate_proposals_sql)} candidates via SQL filters.")
            
            sql_filtered_proposal_ids = [p.id for p in candidate_proposals_sql]

            # 2. Get proposals based on semantic search (VectorDB query)
            candidate_proposals_semantic: List[Dict[str, Any]] = []
            if content_keywords:
                query_embedding = await self.llm_service.generate_embedding(content_keywords)
                if query_embedding:
                    # If we have SQL results, we can pass their IDs to VectorDBService to narrow the semantic search space, if supported and efficient.
                    # Or, perform semantic search more broadly and then intersect.
                    # For simplicity, let's search broadly or filter if SQL results are very few.
                    # `search_proposal_embeddings` can take `filter_proposal_ids`.
                    # If we have SQL results, use them as a pre-filter for semantic search if the list isn't too large.
                    # If no SQL filters were applied, sql_filtered_proposal_ids will be empty, so no filter for semantic search.
                    
                    # Decide on filter_ids for semantic search:
                    # If structured filters were applied AND returned results, search within those.
                    # Otherwise, search all proposals.
                    ids_for_semantic_filter = sql_filtered_proposal_ids if (status_filter or type_filter or deadline_range) and sql_filtered_proposal_ids else None
                    
                    raw_semantic_results = await self.vector_db_service.search_proposal_embeddings(
                        query_embedding=query_embedding,
                        top_n=10, # Get more initial results for potential intersection
                        filter_proposal_ids=ids_for_semantic_filter 
                    )
                    if raw_semantic_results:
                        candidate_proposals_semantic = raw_semantic_results
                        logger.info(f"Found {len(candidate_proposals_semantic)} candidates via semantic search (filtered by SQL: {ids_for_semantic_filter is not None}).")
                else:
                    logger.warning("Could not generate embedding for content_keywords.")
            
            semantic_filtered_proposal_ids = []
            if candidate_proposals_semantic:
                for hit in candidate_proposals_semantic:
                    meta = hit.get("metadata", {})
                    if meta and "proposal_id" in meta:
                        try:
                            semantic_filtered_proposal_ids.append(int(meta["proposal_id"]))
                        except ValueError:
                            logger.warning(f"Could not parse proposal_id from semantic search metadata: {meta['proposal_id']}")
            
            # 3. Consolidate results
            final_proposal_ids = set()
            if (status_filter or type_filter or deadline_range): # If SQL filters were applied
                if content_keywords and candidate_proposals_semantic: # And semantic search also ran
                    # Intersect SQL results with Semantic results
                    final_proposal_ids = set(sql_filtered_proposal_ids).intersection(set(semantic_filtered_proposal_ids))
                    logger.info(f"Intersected SQL ({len(sql_filtered_proposal_ids)}) and Semantic ({len(semantic_filtered_proposal_ids)}) results: {len(final_proposal_ids)} IDs.")
                else: # Only SQL filters ran, or semantic search yielded nothing
                    final_proposal_ids = set(sql_filtered_proposal_ids)
                    logger.info(f"Using only SQL filter results: {len(final_proposal_ids)} IDs.")
            elif content_keywords and candidate_proposals_semantic: # Only semantic search ran (no SQL filters)
                final_proposal_ids = set(semantic_filtered_proposal_ids)
                logger.info(f"Using only Semantic search results: {len(final_proposal_ids)} IDs.")
            # If neither, final_proposal_ids remains empty

            if not final_proposal_ids:
                logger.info("No proposals found matching the combined criteria.")
                return "I couldn't find any proposals matching your query. You could try rephrasing or broadening your search.", []

            # Fetch full proposal objects
            final_proposals = await proposal_repo.get_proposals_by_ids(list(final_proposal_ids))
            
            if not final_proposals:
                return "I found some potential matches by ID, but couldn't retrieve their full details. Please try again.", []

            # 4. Synthesize answer with LLM
            proposal_summaries = []
            for prop in final_proposals:
                summary = f"Proposal ID: {prop.id}\nTitle: {prop.title}\nStatus: {prop.status}\nType: {prop.proposal_type}"
                if prop.creation_date:
                    summary += f"\nCreated: {prop.creation_date.strftime('%Y-%m-%d %H:%M UTC')}"
                if prop.deadline_date:
                    summary += f"\nDeadline: {prop.deadline_date.strftime('%Y-%m-%d %H:%M UTC')}"
                proposal_summaries.append(summary)
            
            if not proposal_summaries: # Should not happen if final_proposals is not empty
                 return "I couldn't find any proposals matching your query criteria.", []

            # --- New: Gather context from documents attached to these proposals ---
            all_doc_source_details: List[Dict[str, Any]] = [] # New: collect structured source details
            additional_document_contexts_for_prompt = [] # For constructing the prompt

            if len(query_text.split()) > 3: # Arbitrary threshold
                logger.info(f"Query '{query_text}' seems detailed enough to search attached documents for {len(final_proposals)} proposals.")
                for prop in final_proposals:
                    logger.info(f"Searching documents attached to proposal ID {prop.id} for query: '{query_text}'")
                    raw_doc_context, current_prop_doc_source_details = await self._get_raw_document_context_for_query(
                        question_text=query_text, 
                        proposal_id_filter=prop.id,
                        top_n_chunks=3
                    )
                    
                    if raw_doc_context:
                        # We want to provide the raw context directly to the final LLM
                        # Construct a header for this proposal's document context
                        context_header_for_prompt = f"From documents related to Proposal {prop.id} ('{prop.title}'):"
                        additional_document_contexts_for_prompt.append(f"{context_header_for_prompt}\n{raw_doc_context}")
                        all_doc_source_details.extend(current_prop_doc_source_details) # Add sources from this proposal's docs
                        logger.info(f"Added raw context from documents of proposal {prop.id}. Context length: {len(raw_doc_context)}")
                    else:
                        logger.info(f"No significant additional context found in documents for proposal {prop.id} regarding query: '{query_text}'")
            # --- End new section ---
            context_for_llm = "Here are the proposals I found matching your query:\n\n" + "\n\n---\n\n".join(proposal_summaries)
            
            if additional_document_contexts_for_prompt:
                context_for_llm += "\n\n---\n\nAdditionally, here is some context from documents related to these proposals:\n\n" + "\n\n---\n\n".join(additional_document_contexts_for_prompt)

            logger.info(f"=== Context for LLM: {context_for_llm} ===\n\n")
            
            # The actual source details for buttons will be `all_doc_source_details`
            # We might want to de-duplicate `all_doc_source_details` before returning if not already handled by _get_raw_document_context_for_query
            # _get_raw_document_context_for_query now de-duplicates, so all_doc_source_details might have duplicates if same doc linked to multiple relevant proposals.
            # For buttons, we want a unique list.
            final_unique_doc_source_details_for_buttons: List[Dict[str, Any]] = []
            seen_button_doc_ids = set()
            for detail in all_doc_source_details:
                if detail['id'] not in seen_button_doc_ids:
                    final_unique_doc_source_details_for_buttons.append(detail)
                    seen_button_doc_ids.add(detail['id'])
            
            synthesis_prompt = (
                f"{context_for_llm}\n\nUser's original query: '{query_text}'\n\nBased on all the proposal information and any additional document context provided above, "
                f"provide a concise answer to the user's query. "
                f"List the relevant proposals clearly. "
                f"If you use information from the document contexts, clearly indicate which document source supports which part of your answer, referencing them by their title and ID as provided in the context. "
                f"Also, if the user is asking about results for a proposal, remind the user that they can use `/my_vote <proposal_id>` to see their specific vote or submission for any of these proposals, or if they are asking about a proposal, remind the user that they can use `/view_proposal <proposal_id>` to see the proposal details."
            )

            final_answer = await self.llm_service.get_completion(synthesis_prompt)
            if not final_answer:
                return "I found some proposals, but I had trouble summarizing them. You can try viewing them individually.", []
            
            return final_answer, final_unique_doc_source_details_for_buttons # Return structured details for buttons

        else: # Fallback to general document RAG
            logger.info("Intent is query_general_docs, falling back to standard RAG.")
            # Assuming no specific proposal_id is relevant for a general query fallback
            # This call now correctly returns a tuple (answer_text, source_details_list)
            return await self.get_answer_for_question(query_text, proposal_id_filter=None)

    async def link_document_to_proposal_in_vector_store(
        self,
        document_sql_id: int,
        proposal_id: int
    ):
        """
        Updates the metadata of document chunks in the vector store to include the proposal_id.
        This should be called after a document (already processed into chunks) is linked
        to a proposal in the SQL database.
        """
        logger.info(f"Attempting to link document SQL ID {document_sql_id} to proposal ID {proposal_id} in vector store metadata (collection: {DEFAULT_COLLECTION_NAME}).")
        
        success = await self.vector_db_service.assign_proposal_id_to_document_chunks(
            document_sql_id=document_sql_id,
            proposal_id=proposal_id,
            collection_name=DEFAULT_COLLECTION_NAME # Explicitly state, though it's the default
        )

        if success:
            logger.info(f"Successfully initiated update for document SQL ID {document_sql_id} to link with proposal ID {proposal_id} in vector store.")
        else:
            logger.error(f"Failed to update vector store metadata for document SQL ID {document_sql_id} with proposal ID {proposal_id}.")
        return success
 