# Active Context - Sat May 17 17:31:03 PDT 2025

## Current Work Focus
- Finalizing Task 4.2: Ensuring robust vote confirmation UI/UX (ephemeral alerts).
- Preparing to move to Task 4.3: Free-Form Submission (`/submit` Command).

## What's Working
- Multiple-choice proposals display voting buttons correctly.
- Votes are successfully recorded in the `submissions` table.
- **Prominent ephemeral alerts (`query.answer(text=..., show_alert=True)`) for vote confirmation are now working reliably** after refactoring `handle_vote_callback` in `app/telegram_handlers/callback_handlers.py` to call `query.answer()` only once at the end.
- `/propose` command conversational flow is functional.
- DM confirmation for proposal creation is sent (MarkdownV2 issues previously addressed).

## What's Broken
- The `PTBUserWarning` regarding `per_message=False` in `ConversationHandler` still appears on startup. This is a known and currently accepted warning, as changing it to `True` broke `/propose` command detection due to the mix of handler types (CommandHandlers and CallbackQueryHandlers).

## Active Decisions and Considerations
- Confirmed that using a prominent ephemeral alert (`show_alert=True`) is the preferred method for user-specific vote confirmation, rather than attempting to edit the public channel message in a user-specific way.

## Learnings and Project Insights
- The timing and singularity of `query.answer()` calls are critical for `show_alert=True` to function correctly in `python-telegram-bot`.
- Thoroughly testing callback handler behavior, especially UI elements like alerts, is important.

## Current Database/Model State
- `users` table exists.
- `proposals` table exists (includes `target_channel_id`, `channel_message_id`).
- `documents` table exists (includes `raw_content`, `vector_ids`, `proposal_id` FK).
- `submissions` table exists (for recording votes and free-form submissions).
- No schema changes were made in the latest fix; focus was on application logic in callback handlers.

## Next Steps
- Perform thorough manual testing of the vote confirmation alert functionality (Task 4.2).
- Update `tasks.md` to mark relevant sub-items of Task 4.2 as complete.
- Begin implementation of Task 4.3: Free-Form Submission (`/submit` command and `handle_free_form_submission_callback`).
