# Active Context - Sat May 17 21:02:08 PDT 2025

## Current Work Focus
- Addressing pending follow-ups for Task 5.2 (timezone display and results message copy tweak).
- Moving to Task 6.3: Enhance URL Content Extraction.

## What's Working
- `/add_global_doc` command (Task 6.1) is functional.
- `/ask` command (Task 6.2) is now functional.
    - RAG pipeline retrieves relevant document chunks.
    - Source citation includes document titles and IDs.
    - Fallback for missing titles in proposal context documents uses username (e.g., "proposal context by @username").
- Phase 5 tasks related to deadline processing and LLM clustering for free-form proposals.
- Newline rendering in summaries and large Telegram ID handling continue to work.

## What's Broken or Pending
- Timezone display (Task 5.2 To-do): User-facing times are still in UTC, need to be PST.
- Copy Tweak (Task 5.2 To-do): Results message instruction "(DM the bot)" needs to be changed to "(DM @botname)".
- The `PTBUserWarning` regarding `per_message=False` persists (known).

## Active Decisions and Considerations
- Determine the best library/approach for Task 6.3 (Enhance URL Content Extraction).

## Learnings and Project Insights
- Corrected key mismatch (`document_content` vs `text_content`) in `ContextService` for RAG.
- Ensured `title` and `document_sql_id` are correctly retrieved from ChromaDB metadata for source citation in `/ask`.
- Refined title generation for documents added during proposal creation in `message_handlers.py` to use `@username` for better identification and tappability.
- Added functionality to `clear_supabase_data.py` to also clear ChromaDB vector embeddings.

## Current Database/Model State
- No schema changes since the last update.
- ChromaDB vector store can be cleared along with SQL data using the script.

## Next Steps
- Address pending Task 5.2 follow-ups (timezone and copy tweak).
- Begin Task 6.3: Enhance URL Content Extraction.
