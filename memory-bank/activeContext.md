# Active Context - Sun May 18 17:57:02 PDT 2025

## Current Work Focus
- Completed adding comprehensive unit tests for all `app/telegram_handlers` files:
    - `error_handler.py`
    - `message_handlers.py`
    - `submission_command_handlers.py`
- All new and previously added unit tests for services, repositories, and handlers are passing.

## What's Working
- All unit tests for `UserRepository`, `UserService`, `LLMService`, `SchedulingService`, and all `telegram_handlers` are passing.
- `/my_votes` command (Task 7.1) is fully functional.
- URL content extraction (Task 6.3) using `crawl4ai`.
- `/add_global_doc` command (Task 6.1).
- `/ask` command (Task 6.2) with RAG pipeline.
- Core proposal lifecycle, including conversational proposal creation.

## What's Broken or Pending
- **Task 5.2 Follow-ups (Still Pending):**
    - **Timezone Consistency:** Review and ensure all *other* user-facing datetimes are consistently displayed in PST.
    - **Results Message Copy:** Tweak results message copy in `ProposalService` for channel announcements from "(DM the bot)" to "(DM @botname)".
- The `PTBUserWarning` regarding `per_message=False` in the `ConversationHandler` for `/propose` persists (accepted behavior for now).

## Active Decisions and Considerations
- Maintaining high unit test coverage for new and existing critical components.

## Important Patterns and Preferences
- When mocking SQLAlchemy result object methods like `scalar_one()` or `scalar_one_or_none()`, ensure the mock returns the direct data (e.g., model instance or `None`) rather than a coroutine, as these methods are synchronous on the (awaited) result object.
- For `pytest` `caplog` fixture: if expected logs are not appearing, use `caplog.set_level(logging.LEVEL, logger="optional.logger.name")` to ensure correct capture.
- When asserting mock calls with complex arguments (like other mocks), prefer checking `call_args` (positional `args` tuple and keyword `kwargs` dict) directly over `assert_called_once_with()` if the latter shows identical expected/actual calls but still fails, as this can be due to mock object comparison intricacies.

## Learnings and Project Insights
- Refined understanding of `AsyncMock` behavior, particularly with SQLAlchemy result proxy methods.
- Importance of explicit log level setting for `caplog` in tests.
- Robust strategies for asserting mock call arguments, especially when positional vs. keyword arguments are involved.
- **`error_handler.py` Test (`test_error_handler_no_update_object`):** The interaction of `str()`, `json.dumps()`, and `html.escape()` on non-`Update` objects in the error handler requires careful consideration for log assertions. `json.dumps()` on a string input wraps it in additional quotes.
- **`message_handlers.py` Test (`test_handle_ask_context_no_context_success`):** Imports for `telegram` library components are needed even if they are only used within mock object setups (e.g., `InlineKeyboardButton` for a mock return value).

## Current Database/Model State
- No schema changes during this unit testing phase for handlers.

## Next Steps
- Address pending Task 5.2 follow-ups:
    - Ensure consistent PST display for all user-facing times.
    - Update results message copy to use "(DM @botname)".
- Begin Phase 7, Task 7.3: Implement `/proposals <proposal_id>` command (view proposal details).
