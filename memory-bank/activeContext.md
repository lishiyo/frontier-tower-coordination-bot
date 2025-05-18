# Active Context - Sun May 18 15:50:23 PDT 2025

## Current Work Focus
- Completed Task 7.1: Implement `/my_votes` Command, including all associated bug fixes (newline rendering, timestamp formatting to PST, Markdown escaping) and documentation updates (`tasks.md`, `bot_commands.md`).
- Preparing to address pending items from Task 5.2 and then move to Task 7.2.

## What's Working
- `/my_votes` command (Task 7.1) is fully functional:
    - Correctly fetches and displays user submission history.
    - Newline characters are rendered properly in the output.
    - Timestamps are displayed in PST using the `format_datetime_for_display` utility.
    - MarkdownV2 formatting is correct, including escaped special characters.
- URL content extraction (Task 6.3) using `crawl4ai` with JavaScript rendering and appropriate filters.
- `/add_global_doc` command (Task 6.1) for admin document management.
- `/ask` command (Task 6.2) with RAG pipeline and source citation.
- Core proposal lifecycle (creation, voting, deadline processing, results announcement) is largely operational.

## What's Broken or Pending
- **Task 5.2 Follow-ups (Still Pending):**
    - **Timezone Consistency:** While `/my_votes` now uses PST, review and ensure all *other* user-facing datetimes (e.g., proposal deadlines shown in channel messages, result announcement timestamps) are consistently displayed in PST.
    - **Results Message Copy:** Tweak the results message copy in `ProposalService` for channel announcements from "(DM the bot)" to "(DM @botname)".
- The `PTBUserWarning` regarding `per_message=False` in the `ConversationHandler` for `/propose` persists (known and accepted for now as `per_message=True` broke command detection).

## Active Decisions and Considerations
- Prioritizing the remaining follow-ups from Task 5.2 before diving deep into new Phase 7 tasks.

## Important Patterns and Preferences
- Leverage existing utility functions (e.g., `format_datetime_for_display`) for common formatting tasks to ensure consistency.
- Maintain rigorous attention to string escaping nuances for Python and Telegram's MarkdownV2, especially when dealing with f-strings and special characters.

## Learnings and Project Insights
- The choice between raw f-strings (`fr"..."`) and regular f-strings (`f"..."`) significantly impacts how escape sequences like `\\n` are interpreted. Regular f-strings are necessary if `\\n` is intended to produce an actual newline, which then requires vigilant manual escaping of Markdown special characters within the string content.
- Double escaping (e.g., `\\-\\-` in an f-string) can be required when a character is special to both Python's string parsing and MarkdownV2.

## Current Database/Model State
- No schema changes since the addition of `crawl4ai` as a library dependency (which did not alter the database schema itself).
- The `clear_supabase_data.py` script remains available for resetting database and vector store content if needed.

## Next Steps
- Address pending Task 5.2 follow-ups:
    - Ensure consistent PST display for all user-facing times.
    - Update results message copy to use "(DM @botname)".
- Begin Phase 7, Task 7.2: Implement `/proposals open` and `/proposals closed` commands.
