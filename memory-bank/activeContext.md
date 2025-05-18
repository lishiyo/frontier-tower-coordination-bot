# Active Context - Sat May 17 18:09:20 PDT 2025

## Current Work Focus
- Task 4.3: Free-Form Submission (`/submit` Command) is now working, including the prefilled version from the deep-link button.
- Updating documentation based on the resolution of the `@botname submit ...` issue.

## What's Working
- `/submit <proposal_id> <text>` command works as expected.
- The "Submit Your Idea" button in channel messages (which deep-links to a DM) now correctly leads to a prefilled command `@botname submit <id> <text>` that is successfully parsed and handled.
- `handle_prefilled_submit` in `app/telegram_handlers/submission_command_handlers.py` now correctly parses the `@botname submit <id> <text>` format.
- `query_to_prefill` in `app/telegram_handlers/command_handlers.py` (for the deep-link start payload) now generates `submit <id> ` (without a leading `/`) which, when used with `switch_inline_query_current_chat`, correctly results in `@botname submit <id> `.
- Multiple-choice proposals display voting buttons correctly.
- Votes are successfully recorded in the `submissions` table.
- **Prominent ephemeral alerts (`query.answer(text=..., show_alert=True)`) for vote confirmation are now working reliably** after refactoring `handle_vote_callback` in `app/telegram_handlers/callback_handlers.py` to call `query.answer()` only once at the end.
- `/propose` command conversational flow is functional.
- DM confirmation for proposal creation is sent (MarkdownV2 issues previously addressed).

## What's Broken
- The `PTBUserWarning` regarding `per_message=False` in `ConversationHandler` still appears on startup. This is a known and currently accepted warning, as changing it to `True` broke `/propose` command detection due to the mix of handler types (CommandHandlers and CallbackQueryHandlers).

## Active Decisions and Considerations
- Confirmed that using a prominent ephemeral alert (`show_alert=True`) is the preferred method for user-specific vote confirmation, rather than attempting to edit the public channel message in a user-specific way.
- The current solution for handling `@botname submit...` (a separate regex handler) is effective.

## Learnings and Project Insights
- `switch_inline_query_current_chat` prepends `@botname` (the bot's username) to the provided query. If the query is intended to be a command like `/submit`, this results in `@botname /submit...`.
- Standard `CommandHandler` in `python-telegram-bot` does not recognize `@botname /command...` as a command. It expects `/command` or `/command@botname`.
- To handle commands prefilled by `switch_inline_query_current_chat` that originally started with `/`, the prefill query should omit the leading `/` (e.g., `submit <id>`), resulting in `@botname submit <id>`. A separate `MessageHandler` with a regex is then needed to parse this specific format.
- Debugging regex issues can benefit from logging `repr(text_to_match)` and `repr(pattern)` to uncover hidden characters or discrepancies. When `repr()` shows clean strings but matching still fails, iteratively testing parts of the regex or using more general capturing groups initially can help isolate the problematic part of the pattern or text.
- The timing and singularity of `query.answer()` calls are critical for `show_alert=True` to function correctly in `python-telegram-bot`.
- Thoroughly testing callback handler behavior, especially UI elements like alerts, is important.

## Current Database/Model State
- `users` table exists.
- `proposals` table exists (includes `target_channel_id`, `channel_message_id`).
- `documents` table exists (includes `raw_content`, `vector_ids`, `proposal_id` FK).
- `submissions` table exists (for recording votes and free-form submissions).
- No schema changes were made in the latest fix; focus was on application logic in callback handlers.

## Next Steps
- Update `progress.md` and `bot_commands.md`.
- Consider if any other commands use `switch_inline_query_current_chat` and might need similar adjustments.
- Continue with any remaining sub-tasks for Task 4.3 or move to the next task.
