# Active Context - Sat May 17 20:15:00 PDT 2025

## Current Work Focus
- Testing the `/ask` command functionality (Task 6.2).

## What's Working
- `/add_global_doc` command (Task 6.1) is now functional after refactoring service instantiation within `admin_command_handlers.py`.
- Phase 5 tasks related to deadline processing and LLM clustering for free-form proposals.
- Newline rendering in summaries and large Telegram ID handling continue to work.

## What's Broken or Pending
- `/ask` command (Task 6.2) needs testing and verification.
- Timezone display (Task 5.2 To-do): User-facing times are still in UTC, need to be PST.
- Copy Tweak (Task 5.2 To-do): Results message instruction "(DM the bot)" needs to be changed to "(DM @botname)".
- The `PTBUserWarning` regarding `per_message=False` persists (known).

## Active Decisions and Considerations
- Proceed with testing the `/ask` command to ensure RAG functionality is operational.

## Learnings and Project Insights
- Refactoring `admin_command_handlers.py` to instantiate services (like `ContextService`) directly with a local `AsyncSessionLocal` context manager resolved `AttributeError` and `TypeError` issues related to the previous `application.services` bundle. This approach is more robust for services requiring database sessions.
- Ensured `source_type` in `admin_command_handlers.py` for `add_global_doc` uses specific values (e.g., `admin_global_text`, `admin_global_url`) to align with `ContextService` expectations, resolving an `Invalid source_type` error.
- The `/add_global_doc` command now correctly handles cases where document content is provided directly with the command or in a follow-up message.

## Current Database/Model State
- No schema changes since the last update (BigInteger for Telegram IDs).

## Next Steps
- Test the `/ask` command functionality (Task 6.2).
- Address pending Task 5.2 follow-ups (timezone and copy tweak).
