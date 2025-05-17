# Active Context - Sat May 17 00:27:46 PDT 2025

## Current Work Focus
- Completed Task 3.3: Context Service Setup.
    - `app/core/context_service.py` is implemented and unit tested.
    - This service handles fetching content (text/URL), chunking, embedding generation, and storage in SQL (DocumentRepository) and VectorDB (VectorDBService).
- Preparing for Task 3.4: ConversationHandler for `/propose`.

## What's Working
- `LLMService` is functional.
- `VectorDBService` is functional.
- `ContextService` (`app/core/context_service.py`) is functional:
    - `process_and_store_document` successfully processes and stores text and URL content.
    - Interactions with `LLMService`, `DocumentRepository`, and `VectorDBService` are working.
- Unit tests for `ContextService` (`tests/unit/core/test_context_service.py`) are passing, including fixes for `httpx` client mocking.

## What's Broken
- No known issues related to the completed Task 3.3.

## Active Decisions and Considerations
- The `_fetch_content_from_url` method in `ContextService` currently uses a basic `response.text`. A TODO exists to add more robust HTML parsing or content extraction (e.g., using a library like `trafilatura` or `beautifulsoup4`) for better quality text from web pages.

## Learnings and Project Insights
- Accurate mocking of asynchronous context managers like `httpx.AsyncClient` is essential for reliable unit tests. This involves mocking `__aenter__` and `__aexit__` and ensuring the yielded client and its response objects are correctly configured.
- For Python scripts within a package that use absolute imports, direct execution (`python path/to/script.py`) can fail with `ModuleNotFoundError`. Running as a module (`python -m package.module`) or adjusting `sys.path` for test/example scripts are common solutions.

## Current Database/Model State
- `users` table exists.
- `proposals` table exists (includes `target_channel_id`).
- `documents` table exists (includes `id`, `title`, `content_hash`, `source_url`, `upload_date`, `vector_ids` (JSON), `proposal_id` (nullable FK)).
- No new DB schema changes in this step.

## Next Steps
- Continue with Phase 3: Conversational Proposal Creation & Initial Context.
    - Task 3.4: ConversationHandler for `/propose`.
        - Refactor `propose_command` in `app/telegram_handlers/command_handlers.py` to use `ConversationHandler`.
        - Define states: `ASK_DURATION`, `ASK_CONTEXT`.
        - Implement handlers for these states.
