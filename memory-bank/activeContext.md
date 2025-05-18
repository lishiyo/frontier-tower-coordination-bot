# Active Context - Sat May 17 19:25:21 PDT 2025

## Current Work Focus
- Addressing remaining to-do items for Task 5.2:
    - Adjusting user-facing timezone displays in messages from UTC to PST.
    - Updating results message copy from "(DM the bot)" to "(DM @botname)".

## What's Working
- **Newline Rendering in Summaries:** Free-form proposal result summaries now correctly render newlines in Telegram messages.
- **Task 5.3 (LLM Clustering for Free-Form Proposals):** Implemented and integrated.
- **Large Telegram ID Handling:** Proposal creation, user registration, and voting are functioning correctly with large Telegram User IDs.
- Scheduler and deadline processing (Tasks 5.1 & 5.2) continue to function.

## What's Broken or Pending
- **Timezone Display (Task 5.2 To-do):** User-facing times (e.g., "Voting ends", "Deadline set for") are still in UTC. Needs to be PST.
- **Copy Tweak (Task 5.2 To-do):** The results message instruction "(DM the bot)" needs to be changed to "(DM @botname)".
- The `PTBUserWarning` regarding `per_message=False` persists (known).

## Active Decisions and Considerations
- Prioritize fixing the timezone and copy tweak next as they are small follow-ups to Task 5.2.

## Learnings and Project Insights
- Newline handling in strings that will be escaped for protocols like MarkdownV2 requires ensuring the `\n` character is an actual newline and not a literal backslash followed by 'n' before the escaping function is called.

## Current Database/Model State
- `users.telegram_id` is `BigInteger`.
- `submissions.submitter_id` is `BigInteger`.
- `proposals.proposer_telegram_id` is `BigInteger`.
- No schema changes anticipated for the immediate next tasks.

## Next Steps
- Implement the timezone display adjustment (PST for user-facing times).
- Implement the copy tweak for the results message ("(DM @botname)").
- Proceed to Phase 6 tasks (RAG for `/ask`, admin document management).
