# Active Context - Mon May 19 16:36:24 PDT 2025

## Current Work Focus
- Successfully resolved an issue with associating `proposal_id` to document chunks in ChromaDB.
- The core problem was that documents added during proposal creation were processed and stored in ChromaDB *before* a `proposal_id` was generated. 
- Implemented a new mechanism to update the ChromaDB chunk metadata with the `proposal_id` *after* the proposal is created and the document is linked to it in the SQL database.
- This ensures that document context relevant to a specific proposal can be correctly retrieved when filtering by `proposal_id`.

## What's Working
- The two-stage process for document ingestion and proposal linking:
    1. Document content (added during proposal creation) is processed and its chunks are stored in ChromaDB (`general_context` collection) without an initial `proposal_id` in their metadata.
    2. After the proposal is created and the SQL link between the document and proposal is established, a new function `ContextService.link_document_to_proposal_in_vector_store` is called.
    3. This function updates the metadata of the relevant document chunks in ChromaDB to include the correct `proposal_id`.
- The `VectorDBService.assign_proposal_id_to_document_chunks` method is now more robust in handling data from `collection.get()`, including potential mismatches in ID and metadata list lengths from ChromaDB.
- The `/ask` command, when needing to fetch context for a specific proposal from general documents (via `_get_raw_document_context_for_query` with a `proposal_id_filter`), should now work correctly due to the metadata being properly linked.

## What's Broken or Pending
- **Task 5.2 Follow-ups (Still Pending from previous context):**
    - **Timezone Consistency:** Review and ensure all *other* user-facing datetimes are consistently displayed in PST.
    - **Results Message Copy:** Tweak results message copy in `ProposalService` for channel announcements from "(DM the bot)" to "(DM @botname)".

## Active Decisions and Considerations
- The current solution adds complexity by requiring an explicit update step to ChromaDB metadata post-SQL-linking. While effective, future optimizations might explore if proposal creation and initial document association can be managed in a way that allows `proposal_id` to be available during the initial ChromaDB storage for these specific documents.

## Important Patterns and Preferences
- When dealing with data dependencies between different storage systems (SQL and VectorDB), ensure that update propagation mechanisms are in place if one system's update requires metadata changes in another.

## Learnings and Project Insights
- Metadata synchronization is crucial for effective filtering in RAG systems that combine structured (SQL) and unstructured/vector (ChromaDB) data.
- Thoroughly understanding the return signatures of library methods (e.g., ChromaDB `get()` vs `query()`) is vital to avoid indexing errors.
- Database session management and service instantiation scope are critical for ensuring data integrity, especially in asynchronous applications.

## Current Database/Model State
- No direct schema changes were made in this iteration. The fix involved new service methods and updated logic for metadata handling in the vector database.