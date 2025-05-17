# Active Context - Sat May 17 01:24:52 PDT 2025

## Current Work Focus
- Finalizing Task 3.4: ConversationHandler for `/propose` (most sub-items implemented and tested).
- Preparing for Task 3.5: (Utility) Implement Viewing of Stored Document Chunks.

## What's Working
- Conversational proposal creation flow in `app/telegram_handlers/message_handlers.py` and `app/telegram_handlers/callback_handlers.py` is largely functional up to and including context processing.
- `handle_ask_context` correctly uses `ContextService.process_and_store_document` and handles the returned document ID.
- Error with `source_type` (expecting `user_text`/`user_url`) in `ContextService` interaction has been resolved.
- Error with `document.id` (expecting integer ID) in `handle_ask_context` has been resolved.

## What's Broken
- Final manual testing for all paths/edge cases of Task 3.4 (conversational propose) might still be pending.
- The `ASK_CHANNEL` state logic, though defined, is not part of the active flow (deferred to Task 8.8).

## Active Decisions and Considerations
- Task 3.5 (viewing stored document chunks) created and prioritized to allow better verification of context processing.
- Task 6.3 (Enhance URL Content Extraction) created, noting `crawl4ai` as a preferred library for future implementation to improve RAG quality from URLs.
- The `_fetch_content_from_url` in `ContextService` still uses basic `response.text` and needs enhancement (now tracked in Task 6.3).

## Learnings and Project Insights
- Careful attention to expected data types (e.g., integer IDs vs. model objects) and string/enum values is crucial when integrating different services/modules.
- Iteratively adding utility tasks (like viewing stored data) can significantly aid in debugging and verifying complex data processing pipelines.

## Current Database/Model State
- `users` table exists.
- `proposals` table exists (includes `target_channel_id`).
- `documents` table exists (includes `id`, `title`, `content_hash`, `source_url`, `upload_date`, `vector_ids` (JSON), `proposal_id` (nullable FK)).
- No new DB schema changes in this step.

## Next Steps
- Complete any remaining manual testing for Task 3.4.
- Proceed with Task 3.5: (Utility) Implement Viewing of Stored Document Chunks.
- Address Follow-up Task from 3.4: Refactor repository methods in `DocumentRepository` (`add_document` and `link_document_to_proposal`) to not commit, ensuring the `handle_ask_context` handler manages the entire transaction for atomicity.
