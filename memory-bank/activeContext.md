# Active Context - Sun May 18 19:18:18 PDT 2025

## Current Work Focus
- Successfully completed Task 7.3, including full unit testing for the `/proposals` command (with open/closed filters via arguments and inline buttons) and its callback handler (`handle_proposal_filter_callback`).
- Fixed unit tests for `submission_command_handlers.py` (`submit_command`, `handle_prefilled_submit`).

## What's Working
- The `/proposals` command is fully functional and tested, including argument-based filtering and inline button filtering.
- `handle_proposal_filter_callback` correctly processes button presses and updates messages.
- `submit_command` and `handle_prefilled_submit` are functioning correctly and have passing unit tests.
- All unit tests for `proposal_command_handlers.py`, `callback_handlers.py` (related to proposal filtering), and `submission_command_handlers.py` are now passing.
- Previous functionalities (URL extraction, RAG, admin doc management, core proposal lifecycle, `/my_votes`) remain operational.

## What's Broken or Pending
- **Task 5.2 Follow-ups (Still Pending from previous context):**
    - **Timezone Consistency:** Review and ensure all *other* user-facing datetimes are consistently displayed in PST.
    - **Results Message Copy:** Tweak results message copy in `ProposalService` for channel announcements from "(DM the bot)" to "(DM @botname)".
- The `PTBUserWarning` regarding `per_message=False` in the `ConversationHandler` for `/propose` persists (accepted behavior for now).

## Active Decisions and Considerations
- Continue maintaining high unit test coverage for all new features and critical bug fixes.

## Important Patterns and Preferences
- When mocking SQLAlchemy result object methods, return direct data, not coroutines.
- Use `caplog.set_level()` for targeted log capture in tests.
- Inspect `mock.call_args` for complex mock call assertions.
- Note `json.dumps()` behavior on string inputs for error handler logging.
- Import all `telegram` components needed for mock setups in test files.

## Learnings and Project Insights
- **MarkdownV2 Escaping in Tests:** Precisely matching string literals (especially backslash usage for MarkdownV2 special characters) with the `Actual` output from `pytest` is critical for assertion success in Telegram message formatting tests.
- **Handler Guard Clauses & Mocks:** Ensure mock inputs for unit tests (e.g., `update.message.text`) are sufficient to pass initial guard clauses in handlers, otherwise the main logic path won't be tested.
- **Regex and Case Sensitivity:** When using `re.IGNORECASE` for matching, remember that subsequent comparisons on captured groups (e.g., `match.group(1) == bot_username`) will still be case-sensitive unless explicitly handled (e.g., using `.lower()`).

## Current Database/Model State
- No schema changes during the completion of Task 7.3 or the recent test fixes.

## Next Steps
- Proceed with Phase 7, Task 7.4: Implement `/edit_proposal` Command (as per `tasks.md`).