# Active Context - Mon May 19 00:06:26 PDT 2025

## Current Work Focus
- Completed Task 9.5.1: Proposal Content Indexing.
  - Implemented functionality in `ProposalService` to generate embeddings for proposal title and description (via `LLMService`) upon creation and edit.
  - Embeddings are stored in a dedicated `proposals_content` collection in ChromaDB via `VectorDBService`.
  - Ensured relevant unit tests for `VectorDBService` and `ProposalService` are passing.

## What's Working
- Proposal creation and editing now correctly index content for semantic search.
- Unit tests for `VectorDBService.add_proposal_embedding`, `VectorDBService.search_proposal_embeddings`, and the indexing logic within `ProposalService.create_proposal` and `ProposalService.edit_proposal_details` are passing.

## What's Broken or Pending
- Manual testing script for proposal embeddings (to create/query sample proposal embeddings).
- **Task 5.2 Follow-ups (Still Pending from previous context):**
    - **Timezone Consistency:** Review and ensure all *other* user-facing datetimes are consistently displayed in PST.
    - **Results Message Copy:** Tweak results message copy in `ProposalService` for channel announcements from "(DM the bot)" to "(DM @botname)".

## Active Decisions and Considerations
- How to best structure the manual test script for proposal embeddings.

## Important Patterns and Preferences
- N/A for this update.

## Learnings and Project Insights
- Importance of correct mock setup for `async` methods, especially ensuring `AsyncMock` is used for methods that are awaited and that `return_value` for these mocks are themselves awaitables if the underlying method returns a coroutine.
- Correctly matching positional vs. keyword arguments in mock assertions is crucial for test accuracy.

## Current Database/Model State
- No SQL schema changes for Task 9.5.1.
- New ChromaDB collection `proposals_content` is now in use.

## Next Steps
- Create a script to manually test proposal embedding and search functionality (similar to `view_document_chunks.py`).