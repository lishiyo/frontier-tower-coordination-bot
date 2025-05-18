# Active Context - Sat May 17 22:10:15 PDT 2025

## Current Work Focus
- Completed Task 6.3 (Enhance URL Content Extraction).
- Preparing to move to Phase 7 tasks, starting with Task 7.1: Implement `/my_votes` Command.

## What's Working
- URL content extraction (Task 6.3) is now significantly improved using `crawl4ai` with appropriate configurations (`java_script_enabled=True`, `wait_until="networkidle"`, and `DefaultMarkdownGenerator` with `PruningContentFilter`). This resolves issues with fetching content from dynamic websites.
- `/add_global_doc` command (Task 6.1) is functional.
- `/ask` command (Task 6.2) is functional, with RAG pipeline and source citation.
- Title generation for proposal context documents includes tappable usernames.
- Core proposal lifecycle (creation, voting, deadline processing, results) is largely functional.

## What's Broken or Pending
- Timezone display (Task 5.2 To-do): User-facing times (e.g., deadlines, result announcements) are still in UTC, need to be consistently displayed in PST.
- Copy Tweak (Task 5.2 To-do): Results message instruction "(DM the bot)" needs to be changed to "(DM @botname)".
- The `PTBUserWarning` regarding `per_message=False` in `ConversationHandler` for `/propose` persists (known and accepted for now).

## Active Decisions and Considerations
- None currently, focusing on moving to the next phase of tasks.

## Learnings and Project Insights
- `crawl4ai` integration requires careful configuration for dynamic sites. `wait_until="networkidle"` is a key setting.
- Debugging discrepancies between standalone script behavior and integrated application behavior is important, often pointing to environment or initialization differences.
- Consistent metadata handling and escaping for Telegram messages remain important for robust functionality.

## Current Database/Model State
- No schema changes since the last update (addition of `crawl4ai` is a library dependency, not a schema change).
- ChromaDB vector store and SQL data can be cleared using `clear_supabase_data.py`.

## Next Steps
- Address pending Task 5.2 follow-ups (timezone and copy tweak for results messages).
- Begin Phase 7, Task 7.1: Implement `/my_votes` Command.
