# Active Context - Sat May 17 18:44:38 PDT 2025

## Current Work Focus
- Successfully resolved MarkdownV2 parsing errors for results messages in `ProposalService.process_expired_proposals`.
- Scheduler and deadline processing (Tasks 5.1 & 5.2) are now functioning correctly, including posting results to channels.
- Addressing new to-do items for Task 5.2: timezone adjustments and copy tweaks for results messages.
- Next major task: Task 5.3 (LLM Clustering for Free-Form Proposals).

## What's Working
- **Results Posting:** Messages for both multiple-choice and free-form proposal results are now correctly formatted and sent to Telegram without MarkdownV2 parsing errors.
    - Fixed by ensuring all user-generated content and specific punctuation (like parentheses around percentages and in static instructional text) are escaped using `telegram_utils.escape_markdown_v2`.
    - Escaping the leading hyphen (`\-`) for list items in the vote breakdown was a key fix for multiple-choice results.
- Scheduler, deadline job, outcome calculation, and database updates for expired proposals are working as implemented in Tasks 5.1 & 5.2.
- All previously working features remain stable.

## What's Broken or Pending
- **LLM Clustering (Task 5.3):** Still pending.
- **Timezone Display:** User-facing times (e.g., "Voting ends", "Deadline set for") are currently in UTC. Task 5.2 has a new to-do to display these in PST.
- **Copy Tweak:** The results message instruction "(DM the bot)" needs to be changed to "(DM @botname)" as per new to-do in Task 5.2.
- The `PTBUserWarning` regarding `per_message=False` persists (known).

## Active Decisions and Considerations
- Continue with 1-minute scheduler interval for testing the upcoming timezone and copy changes.

## Learnings and Project Insights
- Telegram's MarkdownV2 parser is very strict. Every special character `_[]()~>#+-=|{}.!` must be escaped if it's not part of a deliberate Markdown structure. This applies to characters in f-string literals as well as dynamic content.
- When constructing messages with lists, even standard list markers like `- ` can cause issues if other parts of the message or list item content confuse the parser. Sometimes, escaping the list marker itself (`\- `) is necessary.
- Iterative debugging with `repr()` of the final message string is crucial for identifying subtle MarkdownV2 parsing issues.

## Current Database/Model State
- No schema changes. Functionality relies on existing schema.

## Next Steps
- Implement the timezone display adjustment (PST for user-facing times) in relevant message formatting locations.
- Implement the copy tweak for the results message ("(DM @botname)").
- Update `progress.md`.
- Proceed to Task 5.3: `LLMService.cluster_and_summarize_texts`.
