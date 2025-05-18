# Active Context - Sat May 17 19:18:14 PDT 2025

## Current Work Focus
- Addressing a newline display bug in free-form proposal result summaries. The `\n` characters in the LLM-generated summary are appearing as raw text in the Telegram message instead of rendering as newlines.

## What's Working
- **Task 5.3 (LLM Clustering for Free-Form Proposals):** Implemented and integrated. Free-form proposals now generate clustered summaries upon closing.
- **Large Telegram ID Handling:** Proposal creation, user registration, and voting are now functioning correctly with large Telegram User IDs after changing `telegram_id`, `submitter_id`, and `proposer_telegram_id` columns to `BigInteger` and applying corresponding database migrations.
- Scheduler and deadline processing (Tasks 5.1 & 5.2) continue to function.

## What's Broken or Pending
- **Newline Rendering in Summaries:** The `\n` in the free-form proposal result summaries (e.g., "Summary of themes:\nTheme 1...") is not being interpreted as a newline in the final Telegram message.
- **Timezone Display:** User-facing times (e.g., "Voting ends", "Deadline set for") are still in UTC. Task 5.2 has a to-do to display these in PST.
- **Copy Tweak:** The results message instruction "(DM the bot)" needs to be changed to "(DM @botname)" (Task 5.2 to-do).
- The `PTBUserWarning` regarding `per_message=False` persists (known).

## Active Decisions and Considerations
- Investigate whether the newline issue is due to how the string is constructed in `ProposalService`, how it's escaped by `telegram_utils.escape_markdown_v2`, or an interaction with Telegram's MarkdownV2 parsing for complex multi-line strings.

## Learnings and Project Insights
- Database schema design for identifiers sourced from external systems (like Telegram IDs) must anticipate their maximum possible size. `BIGINT` is generally safer than `INTEGER` for such cases.
- Thoroughly checking all related tables and foreign keys during such a data type change is essential to avoid follow-on errors.

## Current Database/Model State
- `users.telegram_id` is `BigInteger`.
- `submissions.submitter_id` is `BigInteger`.
- `proposals.proposer_telegram_id` is `BigInteger`.
- No further schema changes anticipated for the immediate next task.

## Next Steps
- Debug and fix the newline rendering issue in the free-form proposal results messages.
- Implement the timezone display adjustment (PST for user-facing times).
- Implement the copy tweak for the results message ("(DM @botname)").
- Then, proceed to Phase 6 tasks.
