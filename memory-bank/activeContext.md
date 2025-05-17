# Active Context - Sat May 17 13:28:25 PDT 2025

## Current Work Focus
- Testing newly implemented document viewing commands (`/view_doc`, `/view_docs`) as per Task 3.5 and updated `testing_instructions.md`.
- Verifying command handler refactoring (Task 3.5.1).
- Preparing for Task 3.6 (Viewing stored document chunks).

## What's Working
- `NameError` in `context_service.py` is resolved.
- Document viewing commands (`/view_doc`, `/view_docs`) are implemented (Task 3.5).
- Command handlers have been refactored into separate files (Task 3.5.1), and `main.py` has been updated.
- Testing instructions for document viewing have been added to `testing_instructions.md`.
- Conversational proposal creation (Task 3.4) is mostly complete and awaiting final testing.

## What's Broken
- Full manual testing for Task 3.5 (document viewing) is pending.
- Final manual testing for all paths/edge cases of Task 3.4 (conversational propose) might still be pending.

## Active Decisions and Considerations
- Prioritizing testing of the new document commands and the refactored handler structure.

## Learnings and Project Insights
- Modularizing command handlers improves code organization and maintainability.
- Thorough testing instructions are crucial, especially after refactoring or adding new related features.

## Current Database/Model State
- `users` table exists.
- `proposals` table exists (includes `target_channel_id`).
- `documents` table exists (includes `raw_content`, `id`, `title`, `content_hash`, `source_url`, `upload_date`, `vector_ids` (JSON), `proposal_id` (nullable FK)).
- No new DB schema changes in this step beyond what was done for Task 3.5 (adding `raw_content` to documents).

## Next Steps
- Complete manual testing for Task 3.5 (document viewing commands).
- Complete any remaining manual testing for Task 3.4 (Conversational `/propose` flow).
- Proceed with Task 3.6: (Utility) Implement Viewing of Stored Document Chunks (Optional - for Debugging).
- Address Follow-up Task from 3.4: Refactor repository methods in `DocumentRepository` (`add_document` and `link_document_to_proposal`) to not commit, ensuring the `handle_ask_context` handler manages the entire transaction for atomicity.
