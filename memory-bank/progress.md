# Progress Log

## Sun May 18 20:27:16 PDT 2025

**Completed:**
- Refactored `my_proposals_command`:
    - Moved the command handler function from `app/telegram_handlers/proposal_command_handlers.py` to `app/telegram_handlers/user_command_handlers.py`.
    - Updated imports and dependencies in both files accordingly.
    - Moved the corresponding unit tests from `tests/unit/telegram_handlers/test_proposal_command_handlers.py` to `tests/unit/telegram_handlers/test_user_command_handlers.py`.
    - Updated patch paths and imports in the unit test files.
    - Modified `main.py` to reflect the new location of `my_proposals_command`.
- Ensured all related unit tests pass after the refactoring.

**Learnings & Fixes:**
- Refactoring command handlers and their tests requires careful updates to import paths and mock patch locations to maintain test integrity.

**Next Steps:**
- Continue with next planned task as per `tasks.md`.

## Sun May 18 19:18:18 PDT 2025

**Completed:**
- Task 7.3: `/proposals` command (with inline buttons for open/closed filtering) and its associated callback handler (`handle_proposal_filter_callback`) are now fully functional and unit tested.
- Resolved unit test failures in `tests/unit/telegram_handlers/test_proposal_command_handlers.py` by correcting expected MarkdownV2 string formatting in assertions.
- Resolved unit test failures in `tests/unit/telegram_handlers/test_callback_handlers.py` by correcting expected MarkdownV2 string formatting and logger message assertions.
- Resolved unit test failures in `tests/unit/telegram_handlers/test_submission_command_handlers.py` by:
    - Adjusting the `mock_update_submission` fixture to provide a non-empty `update.message.text` to satisfy handler guard clauses.
    - Correcting the bot username comparison in `handle_prefilled_submit` to be case-insensitive.

**Learnings & Fixes:**
- Reinforced the importance of precise string literal representation for MarkdownV2 escaping when writing `pytest` assertions against Telegram message content.
- Unit tests for handlers with initial guard clauses (e.g., checking `update.message.text`) require mock inputs that satisfy these conditions to ensure the main logic is reached and tested.
- Regex matching for case-insensitivity (`re.IGNORECASE`) must be complemented by case-insensitive comparisons if captured groups are subsequently compared against known strings (e.g., `match.group(1).lower() == bot_username.lower()`).

**Next Steps:**
- Proceed with Phase 7, Task 7.4: Implement `/edit_proposal` Command.

## Sun May 18 18:37:21 PDT 2025

**Completed:**
- Enhanced the `/proposals` command (Task 7.3):
    - When called without arguments, it now presents "Open" and "Closed" inline buttons.
    - Implemented a callback handler (`handle_proposal_filter_callback`) in `app/telegram_handlers/callback_handlers.py` to process these button presses. This handler displays the corresponding filtered list of proposals (open or closed) by editing the original message.
    - Added new callback data constants (`PROPOSAL_FILTER_CALLBACK_PREFIX`, `PROPOSAL_FILTER_OPEN`, `PROPOSAL_FILTER_CLOSED`) to `app/telegram_handlers/conversation_defs.py`.
    - Modified `proposals_command` in `app/telegram_handlers/proposal_command_handlers.py` to show buttons if no arguments are provided, and to handle argument-based calls for "open" or "closed" directly.
    - Registered the new `handle_proposal_filter_callback` in `main.py` with the pattern `^{PROPOSAL_FILTER_CALLBACK_PREFIX}`.

**Learnings & Fixes:**
- Successfully used `InlineKeyboardMarkup` and `InlineKeyboardButton` to provide users with quick filter options for the `/proposals` command directly within the bot's response.
- The `query.edit_message_text()` method is effective for updating the message content after a callback query, providing a seamless user experience by replacing the button prompt with the filtered results.

**Next Steps:**
- Implement unit tests for the updated `/proposals` command behavior in `app/telegram_handlers/proposal_command_handlers.py` and the new `handle_proposal_filter_callback` in `app/telegram_handlers/callback_handlers.py`.

## Sun May 18 17:57:02 PDT 2025

**Completed:**
- Added comprehensive unit tests for the remaining `app/telegram_handlers`:
    - `tests/unit/telegram_handlers/test_error_handler.py` for `app/telegram_handlers/error_handler.py`
    - `tests/unit/telegram_handlers/test_message_handlers.py` for `app/telegram_handlers/message_handlers.py`
    - `tests/unit/telegram_handlers/test_submission_command_handlers.py` for `app/telegram_handlers/submission_command_handlers.py`
- Successfully debugged and fixed all identified issues in these new unit tests, ensuring they pass.

**Learnings & Fixes (Unit Testing - Telegram Handlers):**
- **`error_handler.py` Test (`test_error_handler_no_update_object`):** When testing the `error_handler` with a mock update object that is *not* an instance of `telegram.Update`, the handler internally calls `str()` on the object, then `json.dumps()` on that string. This results in the string being wrapped in quotes (e.g., `"string_content"`) which are then HTML-escaped (e.g., `&quot;string_content&quot;`). Assertions for the logged output must account for this double processing.
- **`message_handlers.py` Test (`test_handle_ask_context_no_context_success`):** A `NameError` for `InlineKeyboardButton` occurred because it was used in a mock setup (`mock_telegram_utils.get_free_form_submit_button.return_value`) but was not imported in the test file. Ensured all necessary `telegram` library components are imported in test files where they are referenced, even if only within mock setups.

**Next Steps:**
- Begin Phase 7, Task 7.2: Implement `/proposals open` and `/proposals closed` commands.


## Sun May 18 17:20:11 PDT 2025

**Completed:**
- Added comprehensive unit tests for several key service and repository layers:
    - `tests/unit/persistence/repositories/test_user_repository.py` for `app/persistence/repositories/user_repository.py`
    - `tests/unit/core/test_user_service.py` for `app/core/user_service.py`
    - `tests/unit/services/test_llm_service.py` for `app/services/llm_service.py`
    - `tests/unit/services/test_scheduling_service.py` for `app/services/scheduling_service.py`
- Successfully debugged and fixed all identified issues in the newly created unit tests, ensuring they pass.

**Learnings & Fixes (Unit Testing Focus):**
- **SQLAlchemy `AsyncMock` for Result Proxies:** When mocking `session.execute()` in SQLAlchemy asynchronous tests, the mock `result` object (returned by `session.execute()`) should have its scalar methods like `scalar_one()` or `scalar_one_or_none()` configured as `MagicMock`s that return the actual data (e.g., a `User` instance or `None`) directly, not as `AsyncMock`s that would return a coroutine. This is because these methods are synchronous on the `Result` object, which is obtained after `await session.execute()`.
- **`pytest caplog` Behavior:** If `caplog.text` is empty in tests where logs are expected, it might be due to the default log level or logger scope. Using `caplog.set_level(logging.INFO)` (or other levels like `logging.ERROR`) or `caplog.set_level(logging.INFO, logger="specific.logger.name")` within the test function ensures that the desired logs are captured.
- **Mock Call Argument Assertions:** When `mock.assert_called_with()` or `mock.assert_called_once_with()` fails with seemingly identical "Expected" and "Actual" calls (especially when mocks are passed as arguments), it can be due to mock object comparison intricacies. A more robust approach is to assert the call count (`mock.assert_called_once()`) and then inspect `mock.call_args` (which provides `args` tuple and `kwargs` dict) to verify positional and keyword arguments individually. This was particularly relevant for distinguishing how `context` was passed (positional vs. keyword) to `send_message_in_chunks`.

**Next Steps:**
- Begin Phase 7, Task 7.2: Implement `/proposals open` and `/proposals closed` commands.

## Sun May 18 15:50:23 PDT 2025

**Completed:**
- Task 7.1: `/my_votes` command is now fully functional.
    - Fixed newline rendering issues in `app/telegram_handlers/user_command_handlers.py` by switching from raw f-strings to regular f-strings and double-escaping MarkdownV2 special characters (e.g., `\\(` for `(`).
    - Timestamps in `/my_votes` output are now correctly formatted to PST by utilizing `app.utils.telegram_utils.format_datetime_for_display` in `app/core/submission_service.py`.
    - Resolved `SyntaxWarning: invalid escape sequence '\\-'` in `user_command_handlers.py` by using double backslashes for hyphens (`\\-\\-`) in the separator line within regular f-strings.
- Updated `memory-bank/tasks.md` to mark all sub-tasks for Task 7.1 as complete.
- Updated `memory-bank/bot_commands.md` with documentation for the `/my_votes` command.

**Learnings & Fixes:**
- Raw f-strings (`fr"..."`) prevent `\\n` from being processed as newlines. Regular f-strings (`f"..."`) should be used if `\\n` is intended for newlines, which then requires careful manual escaping of any MarkdownV2 special characters within the string itself.
- Reaffirmed the utility of shared formatting functions like `format_datetime_for_display` for consistency.
- Understanding the interplay between Python's string escaping and Telegram's MarkdownV2 escaping is crucial (e.g., needing `\\-\\-` in an f-string to produce `\\-` for MarkdownV2).

**Next Steps:**
- Begin Phase 7, Task 7.2: Implement `/proposals open` and `/proposals closed`.

## Sat May 17 20:15:00 PDT 2025

**Completed:**
- Successfully refactored `app/telegram_handlers/admin_command_handlers.py` for the `/add_global_doc` command (Task 6.1).
    - Services (`ConfigService`, `LLMService`, `VectorDBService`, `ContextService`) are now instantiated directly within the command handlers.
    - `ContextService` uses a local `AsyncSessionLocal` context manager for database sessions within the handler scope.
    - This resolved previous `AttributeError` (related to `context.application.services`) and `TypeError` (related to service `__init__` signatures) issues that arose from the `main_services.py` / `SimpleNamespace` approach for service bundling.
- Corrected `source_type` logic in `admin_command_handlers.py` to pass specific values like `admin_global_text` or `admin_global_url` to `ContextService`, fixing an `Invalid source_type` error.
- Enhanced the `/add_global_doc` command to correctly handle document content provided directly in the command arguments (e.g., `/add_global_doc <content>`) in addition to the conversational flow.
- Task 6.1 (`/add_global_doc`) is now fully functional.

**Learnings & Fixes:**
- The approach of instantiating services directly within handlers (especially those requiring specific session contexts like `ContextService`) is more robust for this project than relying on a global service bundle attached to the `application` object, particularly when dealing with `AsyncSessionLocal`.
- Careful alignment of `source_type` string conventions between calling handlers and service methods is crucial to prevent validation errors.
- Simplified the service access pattern in `admin_command_handlers.py`, removing the need for `main_services.py` and the `application.services` attribute for these handlers.

**Next Steps:**
- Test the `/ask` command functionality (Task 6.2) to ensure the RAG pipeline is working as expected.
- Address pending follow-ups for Task 5.2 (timezone display and results message copy tweak).


## Sat May 17 19:25:21 PDT 2025

**Completed:**
- Fixed newline rendering bug in free-form proposal result summaries. The issue was with how newline characters from the LLM's summary were being incorporated into the final message string before MarkdownV2 escaping.
    - Solution involved explicitly replacing any literal `\\n` or `\n` from the LLM's output with actual `\n` characters in `ProposalService` before constructing the `outcome_text`.

**Learnings & Fixes:**
- When incorporating multi-line text from an external source (like an LLM) into a formatted string that will undergo further escaping (e.g., for Markdown), ensure that newline characters are correctly represented as actual `\n` characters in the string prior to the final escaping step.

**Next Steps:**
- Address remaining to-dos for Task 5.2:
    - Adjust user-facing timezone displays from UTC to PST.
    - Tweak results message copy from "(DM the bot)" to "(DM @botname)".
- Continue with Phase 6: RAG for `/ask` Command & Admin Document Management.

## Sat May 17 19:18:14 PDT 2025

**Completed:**
- Task 5.3: Implement LLM Clustering for Free-Form Proposals.
    - Added `cluster_and_summarize_texts` method to `LLMService`.
    - Integrated this method into `ProposalService.process_expired_proposals` to generate summaries for free-form proposal results.
- Resolved critical database errors related to `telegram_id` size:
    - Changed `User.telegram_id` from `Integer` to `BigInteger`.
    - Changed `Submission.submitter_id` (ForeignKey to `User.telegram_id`) from `Integer` to `BigInteger`.
    - Changed `Proposal.proposer_telegram_id` (ForeignKey to `User.telegram_id`) from `Integer` to `BigInteger`.
    - Successfully created and applied three Alembic migrations to reflect these schema changes in the database (`f1ac7397b643`, `2de06a4f92b0`, `f558c5a9a4d6`).

**Learnings & Fixes:**
- When dealing with external identifiers like Telegram User IDs, it's crucial to use a sufficiently large data type (e.g., `BigInteger`) in all tables where these IDs are stored or referenced (including foreign keys).
- Alembic autogeneration might not always capture all necessary changes for `alter_column` operations, requiring manual verification and population of migration scripts.

**Next Steps:**
- Address newline display bug in free-form proposal result summaries (currently showing raw `\n` instead of rendering a newline).
- Continue with Phase 6: RAG for `/ask` Command & Admin Document Management.

## Sat May 17 18:44:38 PDT 2025

**Completed:**
- Continued Task 5.2: Deadline Checking Job.
    - Resolved `telegram.error.BadRequest: Can't parse entities` errors when posting results messages for both multiple-choice and free-form proposals.
    - Fix involved ensuring all parts of the dynamically constructed results messages (including static text with parentheses and list item markers) were correctly escaped for MarkdownV2, or that text within inline code blocks was not unnecessarily escaped.
        - Key fixes: Escaping parentheses in formatted percentage strings `\(100.0%\)`.
        - Escaping parentheses in static instructional text `\(DM the bot\)`.
        - Escaping the leading hyphen for list items `\- ` in the vote breakdown.

**Learnings & Fixes:**
- Telegram's MarkdownV2 parser requires meticulous escaping of all special characters: `_[]()~>#+-=|{}.!`. This applies to static parts of f-strings as well as dynamic content.
- When MarkdownV2 parsing fails, the specific character flagged by the error (e.g., '-') might be the first point of failure in a complex string, even if that character is a valid Markdown element (like a list hyphen). The root cause could be an interaction with other improperly escaped entities or an overall parsing ambiguity.
- Iterative debugging using `repr()` on the exact message string being sent to Telegram is invaluable for diagnosing these subtle escaping issues.

**Next Steps:**
- Address new to-dos for Task 5.2:
    - Adjust user-facing timezone displays from UTC to PST.
    - Tweak results message copy from "(DM the bot)" to "(DM @botname)".
- Proceed to Task 5.3: Implement LLM Clustering for free-form proposal summaries.

## Sat May 17 18:21:49 PDT 2025

**Completed:**
- **Task 5.1: Scheduling Service Setup**
    - Created `app/services/scheduling_service.py`.
    - Initialized `AsyncIOScheduler`.
    - Added `start_scheduler` and `stop_scheduler` functions.
    - Integrated scheduler start/stop into `main.py` lifecycle, passing the `Application` instance to `start_scheduler`.
- **Task 5.2: Deadline Checking Job**
    - Verified existence of `ProposalRepository.find_expired_open_proposals()`.
    - Implemented `ProposalService.process_expired_proposals()`:
        - Fetches expired proposals.
        - Calculates results for multiple-choice proposals (vote tally).
        - Implements placeholder summarization for free-form proposals.
        - Updates proposal status to "CLOSED" and stores outcome/raw_results.
        - Posts results messages to the proposal's target channel, replying to the original proposal message.
    - Modified `ProposalService.__init__` to accept and store `bot_app` (Application instance) for message sending capabilities.
    - Ensured `ProposalService` instantiation in `app/telegram_handlers/message_handlers.py` (manual edit by user) passes `context.application` as `bot_app`.
    - Defined `check_proposal_deadlines_job` in `SchedulingService` to call `ProposalService.process_expired_proposals()`.
    - Added `check_proposal_deadlines_job` to the scheduler to run at 1-minute intervals (for testing).

**Learnings & Fixes:**
- Services needing to send Telegram messages outside of direct handler flows (e.g., from a scheduler) require access to the `Application` or `Bot` instance.
- Scheduled jobs should manage their own database sessions (e.g., using `AsyncSessionLocal`).
- The `ProposalService` now correctly handles the processing of expired proposals and posts results.

**Next Steps:**
- Manually test the scheduler and deadline processing logic thoroughly.
- Add testing instructions for Phase 5 to `memory-bank/testing_instructions.md`.
- Implement Task 5.3: `LLMService.cluster_and_summarize_texts` for free-form proposal summaries.

## Sat May 17 18:09:20 PDT 2025

**Completed:**
- Task 4.3: Free-Form Submission (`/submit` Command) and Deep-Link Prefill Handling.
    - Modified `query_to_prefill` in `app/telegram_handlers/command_handlers.py` (for `/start submit_...` payload) to generate `submit <id> ` (without leading `/`). This ensures `switch_inline_query_current_chat` correctly forms `@botname submit <id> ...`.
    - Added `handle_prefilled_submit` function to `app/telegram_handlers/submission_command_handlers.py`. This new handler uses regex `^\s*@(\w+)\s+submit\s+(\d+)\s+(.*)$` to capture submissions made via the prefilled text, then validates the bot username and calls the original `submit_command`.
    - Registered `handle_prefilled_submit` as a `MessageHandler` in `main.py` for private chats.
    - Successfully debugged regex matching for `handle_prefilled_submit` after initial attempts failed despite seemingly correct patterns and input strings (verified with `repr()`). The working solution involved capturing the username with `(\w+)` and then comparing it, which proved more robust in this context.

**Learnings & Fixes:**
- `switch_inline_query_current_chat` prepends the bot's username (`@botname`) to the query. If the original query was `/command`, it becomes `@botname /command`.
- Standard `CommandHandler` does not recognize `@botname /command`. It requires `/command` or `/command@botname`.
- For commands initiated via `switch_inline_query_current_chat` (that were originally slash commands), the solution is:
    1. Provide the `query` to `switch_inline_query_current_chat` *without* the leading slash (e.g., `"command args"`).
    2. This results in the user's input field being prefilled with `@botname command args`.
    3. Implement a `MessageHandler` with a regex to capture this specific format (e.g., `^\s*@BOT_USERNAME\s+command\s+(ARG1)\s+(.*)$`).
    4. This handler then typically extracts arguments and calls the underlying logic of the original slash command handler.
- When debugging regex that fails despite `repr()` showing clean strings, simplifying the pattern, using more general capture groups (like `\w+` instead of the escaped username directly in the pattern), and then validating the captured group can sometimes overcome very subtle matching issues.

**Next Steps:**
- Update `bot_commands.md` to reflect the effective `@botname submit <id> ...` alias.
- Continue with any further testing or sub-tasks for Task 4.3.


## Sat May 17 17:31:03 PDT 2025

**Completed:**
- Task 4.2 (Partial): Addressed issues with ephemeral vote confirmation alerts.
    - Refactored `handle_vote_callback` in `app/telegram_handlers/callback_handlers.py` to call `query.answer()` only once at the end of the function.
    - Ensured `show_alert=True` is used for vote confirmation, making the pop-up alert reliably display after a user votes.
- Previously addressed in this session:
    - Fixed vote buttons not appearing for multiple-choice proposals due to enum vs enum.value comparison error in `app/telegram_handlers/message_handlers.py`.
    - Resolved `AttributeError: 'UserService' object has no attribute 'get_user_by_telegram_id'` in `app/core/submission_service.py` by using `register_user_interaction`.
    - Corrected MarkdownV2 parsing errors for DM confirmations in `app/telegram_handlers/message_handlers.py` (e.g., escaping special characters or simplifying message).
    - Investigated and reverted `per_message=True` in `ConversationHandler` for `/propose` as it caused command detection issues. The `per_message=False` warning is noted but accepted.

**Learnings & Fixes:**
- Calling `query.answer()` multiple times or prematurely within a callback handler can prevent `show_alert=True` from working correctly. It should typically be called once at the end.
- The `PTBUserWarning` regarding `per_message=False` in `ConversationHandler` is benign for handlers that mix `CommandHandler` entry points with `CallbackQueryHandler` states if not all handlers are `CallbackQueryHandler`. Reverting to `per_message=False` fixed command detection.

**Next Steps:**
- Continue with Task 4.2:
    - Thoroughly test the vote confirmation alert under various conditions.
    - Mark Task 4.2 sub-items as complete in `tasks.md` based on successful testing.
- Proceed to Task 4.3: Free-Form Submission (`/submit` Command).

## Sat May 17 16:13:24 PDT 2025

**Completed:**
- Task 3.6: (Utility) Implement Viewing of Stored Document Chunks.
    - Added `get_document_chunks(sql_document_id)` method to `app/services/vector_db_service.py`.
    - Created utility script `app/scripts/view_document_chunks.py` to view chunks using the new service method.
- Phase 3 (Conversational Proposal Creation & Initial Context) is now fully complete.

**Learnings & Fixes:**
- ChromaDB's `collection.get()` method with a `where` filter is effective for retrieving specific documents or chunks based on their metadata, such as a `document_sql_id`.

**Next Steps:**
- Begin Phase 4: Voting and Submission Logic.
    - Task 4.1: Define `Submission` SQLAlchemy model and repository.

## Sat May 17 13:28:25 PDT 2025

**Completed:**
- Resolved `NameError: name 'Document' is not defined` in `app/core/context_service.py` by ensuring the `Document` model was correctly imported and available in the scope where type hints were being resolved.
- Task 3.5: Implemented document storage with full content and basic viewing commands (`/view_doc`, `/view_docs`). This includes schema changes, updates to document ingestion, and implementation of the new commands.
- Task 3.5.1: Refactored command handlers by moving them into separate files within `app/telegram_handlers/` (e.g., `document_command_handlers.py`, `proposal_command_handlers.py`) and updated `main.py` imports.
- Added comprehensive testing instructions for document viewing commands (related to Task 3.5) to `memory-bank/testing_instructions.md`.

**Learnings & Fixes:**
- Python's name resolution for type hints, especially within class definitions, can be sensitive. Ensured imports are available before the class definition that uses them as type hints.
- Confirmed the successful refactoring of command handlers into a more modular structure.

**Next Steps:**
- Manually test the document viewing commands (`/view_doc`, `/view_docs`) as per the new instructions in `testing_instructions.md`.
- Complete any remaining manual testing for Task 3.4 (Conversational `/propose` flow).
- Proceed with Task 3.6: (Utility) Implement Viewing of Stored Document Chunks (Optional - for Debugging).
- Address Follow-up Task from 3.4: Refactor repository methods in `DocumentRepository` (`add_document` and `link_document_to_proposal`) to not commit, ensuring the `handle_ask_context` handler manages the entire transaction for atomicity.


## Sat May 17 01:24:52 PDT 2025

**Completed:**
- Task 3.4: ConversationHandler for `/propose` (most sub-items completed).
    - Implemented conversational flow for collecting title, description, proposal type, options, duration, and initial context.
    - Fixed `AttributeError: 'int' object has no attribute 'id'` in `handle_ask_context` by correctly handling the integer document ID returned from `ContextService`.
    - Fixed `Invalid source_type` error by changing `source_type` in `handle_ask_context` to use `user_text` and `user_url` as expected by `ContextService`.
- Updated `memory-bank/tasks.md`:
    - Moved multi-channel `ASK_CHANNEL` sub-tasks from Task 3.4 to Task 8.8.
    - Added Task 3.5: (Utility) Implement Viewing of Stored Document Chunks.
    - Added Task 6.3: Enhance URL Content Extraction (noting `crawl4ai` as preferred).

**Learnings & Fixes:**
- Ensured `handle_ask_context` correctly processes the integer `document_id` returned by `ContextService.process_and_store_document`.
- Verified that `ContextService` expects `source_type` to end with `_url` or `_text` (e.g., `user_text`, `user_url`).

**Next Steps:**
- Complete any remaining manual testing for Task 3.4 (Conversational `/propose` flow).
- Proceed with Task 3.5: (Utility) Implement Viewing of Stored Document Chunks.
- Address Follow-up Task from 3.4: Refactor repository methods in `DocumentRepository` (`add_document` and `link_document_to_proposal`) to not commit, ensuring the `handle_ask_context` handler manages the entire transaction.


## Sat May 17 00:27:46 PDT 2025

**Completed:**
- Task 3.3: Context Service Setup
    - Created `app/core/context_service.py`.
    - Implemented `ContextService.process_and_store_document` method, including:
        - URL fetching (`_fetch_content_from_url` using `httpx`).
        - Text chunking (using `app.utils.text_processing.simple_chunk_text`).
        - Embedding generation via `LLMService`.
        - Document metadata storage in `DocumentRepository`.
        - Embedding storage in `VectorDBService`, linking SQL Document ID and updating SQL document with vector IDs.
    - Wrote unit tests for `ContextService` in `tests/unit/core/test_context_service.py`.
    - Addressed and fixed issues with `httpx.AsyncClient` mocking in asynchronous context managers within the tests.

**Learnings & Fixes:**
- Correctly mocking `httpx.AsyncClient` when used as an asynchronous context manager requires careful setup of `__aenter__` and `__aexit__` methods on the mock instance. `MagicMock` should be used for the client yielded by `__aenter__` and for the response object, especially for synchronous attributes/methods like `response.text` or `response.raise_for_status()`.
- Running Python scripts that are part of a package directly (e.g., `python app/services/some_service.py`) can lead to `ModuleNotFoundError` if they use absolute imports from the package root. This is because the script's directory is added to `sys.path` but not necessarily the project root. Solutions include running as a module (`python -m app.services.some_service`) or temporarily modifying `sys.path` within `if __name__ == '__main__':` blocks for example/testing scripts.

**Next Steps:**
- Continue with Phase 3: Conversational Proposal Creation & Initial Context.
    - Task 3.4: ConversationHandler for `/propose`.


## Sat May 17 00:02:53 PDT 2025

**Completed:**
- Task 3.1: LLM Service Setup
    - Created `app/services/llm_service.py`.
    - Implemented `generate_embedding(text)` using OpenAI API.
    - Implemented `get_completion(prompt)` using OpenAI API.
    - Implemented `parse_natural_language_duration(text)` using OpenAI API:
        - Developed a stricter prompt to instruct the LLM to return only a datetime string in 'YYYY-MM-DD HH:MM:SS UTC' format or 'ERROR_CANNOT_PARSE'.
        - Included current UTC time as context in the prompt for better relative date parsing.
        - Added logic to parse the LLM's string response into a timezone-aware `datetime` object.
    - User confirmed the `parse_natural_language_duration` function is working as expected after prompt refinement.

**Learnings & Fixes:**
- LLMs can be overly verbose. Initial implementation of `parse_natural_language_duration` resulted in the LLM returning explanations along with the date, causing parsing failures.
- Refining prompts to be very explicit about the desired output format (e.g., "Respond with ONLY...") is crucial for reliable parsing of LLM responses.

**Next Steps:**
- Continue with Phase 3: Conversational Proposal Creation & Initial Context.
    - Task 3.2: VectorDB Service Setup & Document Model.

## Fri May 16 22:51:12 PDT 2025

**Completed:**
- Task 2.5: Add Multi-Channel Support to Proposal Model
    - Updated `app/persistence/models/proposal_model.py` to include `target_channel_id`.
    - Generated and edited Alembic migration `cb7185863232_add_target_channel_id_to_proposal.py` to add the new column, update existing rows using `TARGET_CHANNEL_ID` environment variable, and set the column to non-nullable.
    - Updated `app/persistence/repositories/proposal_repository.py` (`add_proposal`) to handle the new field.
    - Updated `app/core/proposal_service.py` (`create_proposal`) to pass `target_channel_id` to the repository.
    - Updated `app/telegram_handlers/command_handlers.py` (`propose_command`) to fetch `TARGET_CHANNEL_ID` from `ConfigService` and pass it to `ProposalService.create_proposal`, and to use the `target_channel_id` from the returned proposal object when posting to the channel.
    - User confirmed the `/propose` command is working after these changes.

**Learnings & Fixes:**
- Corrected a `TypeError` in `propose_command` by ensuring `target_channel_id` was passed to `ProposalService.create_proposal`.
- Emphasized the importance of having the `TARGET_CHANNEL_ID` environment variable available when running Alembic migrations that depend on it for data backfills.

**Next Steps:**
- Begin Phase 3: Conversational Proposal Creation & Initial Context.
    - Task 3.1: LLM Service Setup.

## Fri May 16 22:41:10 PDT 2025

**Completed:**
- Task 2.4: Basic `/propose` Command (Static Duration for now).
    - Implemented `/propose` command handler in `app/telegram_handlers/command_handlers.py`.
    - `ProposalService.create_proposal` now handles basic proposal creation logic.
    - Proposals are posted to the `TARGET_CHANNEL_ID`.
    - DM confirmation sent to proposer.
    - Channel message ID is stored for future updates.
- Addressed `telegram.error.BadRequest` for free-form proposals in channels:
    - Removed `switch_inline_query_current_chat` button from channel messages for free-form proposals in `app/telegram_handlers/command_handlers.py`.
    - Updated `memory-bank/testing_instructions.md` to reflect that channel messages for free-form proposals will use text instructions instead of an interactive button.
- Updated design documents for multi-channel proposal handling:
    - `memory-bank/projectbrief.md`: Updated with multi-channel user stories and functional requirements.
    - `memory-bank/systemPatterns.md`: Updated to reflect multi-channel capabilities in `ProposalService`, `ConfigService`, data flows, and proposal model.
    - `memory-bank/tasks.md`: Added `target_channel_id` to `Proposal` model definition (Task 2.3), clarified its usage in single-channel mode for Task 2.4, and added Task 2.5 for database migration and Task 8.8 for full multi-channel implementation.

**Learnings & Fixes:**
- `switch_inline_query_current_chat` buttons are not suitable for messages posted by a bot to a channel, as they can lead to `telegram.error.BadRequest` if the user hasn't interacted with the bot directly or if the bot's username isn't implicitly known in the channel context. Relying on clear text instructions for such cases is more robust.
- Ensured task list (`tasks.md`) correctly reflects the need for a database migration (Task 2.5) after realizing `target_channel_id` was not part of the initial Task 2.3 implementation.

**Next Steps:**
- Task 2.5: Add Multi-Channel Support to Proposal Model
    - Update the `Proposal` SQLAlchemy model to include `target_channel_id`.
    - Generate and apply an Alembic migration to add the `target_channel_id` column to the `proposals` table, with a default value for existing records.
    - Update repository and service layers to correctly handle the new field.

## Fri May 16 21:25:44 PDT 2025

**Completed:**
- Task 2.2: Implicit User Registration
    - Created `app/core/user_service.py` with `register_user_interaction` method.
    - Modified `start_command` in `app/telegram_handlers/command_handlers.py` to call `UserService.register_user_interaction`.
- Task 2.3: Proposal Model & Repository
    - Defined `Proposal` SQLAlchemy model in `app/persistence/models/proposal_model.py`.
    - Created `ProposalRepository` in `app/persistence/repositories/proposal_repository.py` with methods for adding, getting, and updating proposals.
    - Addressed issues with Alembic autogeneration:
        - Ensured models are imported in `app/persistence/models/__init__.py`.
        - Explicitly imported model classes in `alembic/env.py`.
        - Set `revision_environment = true` in `alembic.ini`.
        - Manually populated the migration script `0cb97eaf1e36_create_proposal_table.py` when autogeneration still failed to produce a complete script despite `target_metadata` appearing correct.
    - Applied the (manually populated) migration `0cb97eaf1e36_create_proposal_table.py` to create the `proposals` table.
    - Removed debug print statement from `alembic/env.py`.

**Learnings & Fixes:**
- Alembic autogeneration can be sensitive. Even with correct `target_metadata` and model imports, it may fail to detect changes. Setting `revision_environment = true` in `alembic.ini` is crucial. If problems persist, manually creating or populating migration scripts is a viable workaround.
- Ensured `app/persistence/models/__init__.py` imports all model classes.

**Next Steps:**
- Phase 2: User Management and Core Proposal Features (Static)
    - Task 2.4: Basic `/propose` Command (Static Duration for now)

## Fri May 16 21:05:44 PDT 2025

**Completed:**
- Task 2.1: User Model & Repository
    - Defined `User` SQLAlchemy model in `app/persistence/models/user_model.py`.
    - Created `UserRepository` in `app/persistence/repositories/user_repository.py` with `get_or_create_user` and `get_user_by_telegram_id` methods.
    - Populated and applied Alembic migration `8aa34f61aaa0_create_user_table.py` to create the `users` table.

**Learnings & Fixes:**
- Encountered `socket.gaierror` during `alembic upgrade head` due to DNS resolution issues with the Supabase direct database hostname (e.g., `db.<project_ref>.supabase.co`).
- Debugged DNS resolution using `dig @8.8.8.8 <hostname>`, which confirmed the direct DB hostname was not resolving publicly (`ANSWER: 0`).
- The general project API hostname (e.g., `<project_ref>.supabase.co`) and the connection pooler hostname (e.g., `aws-0-<region>.pooler.supabase.com`) were resolvable.
- Resolved the database connection issue by switching the `POSTGRES_HOST` and `POSTGRES_USER` in `.env` to use the Supabase **connection pooler** details. This allowed `alembic upgrade head` to succeed.
- Corrected `app/config.py` to ensure `get_database_url()` properly constructs the connection string from individual `POSTGRES_*` environment variables.
- Added explicit import of `user_model` to `alembic/env.py` for robustness in migration autogeneration.

**Next Steps:**
- Phase 2: User Management and Core Proposal Features (Static)
    - Task 2.2: Implicit User Registration

## Wed May 14 16:29:25 PDT 2025

**Completed:**
- Task 1.5: Implement `/start` and `/help` Commands.
    - Created `app/telegram_handlers/command_handlers.py`.
    - Implemented `start_command` and `help_command`.
    - Registered handlers in `main.py`.
    - Resolved `ImportError` for `DatabaseManager` in `main.py` by commenting out the import.
    - Fixed asyncio event loop errors in `main.py` by refactoring to a synchronous main function.
    - Addressed Telegram message formatting issues by switching to `ParseMode.HTML` in `help_command`.
    - Created initial unit tests for `start_command` and `help_command` in `tests/unit/telegram_handlers/test_command_handlers.py`.
    - Added manual testing instructions to `memory-bank/testing_instructions.md`.

**Learnings & Fixes:**
- Ensured `main.py` correctly uses `config_service.get_bot_token()`.
- Identified and resolved asyncio event loop conflicts caused by `asyncio.run()` and `application.run_polling()`.
- Switched from `ParseMode.MARKDOWN` to `ParseMode.HTML` for more robust message formatting in Telegram, especially for text containing special characters or code examples.
- Confirmed the need for `pytest-asyncio` for running asynchronous tests and advised on installation.

**Next Steps:**
- Phase 2: User Management and Core Proposal Features (Static)
    - Task 2.1: User Model & Repository

## Tue May 13 23:42:07 PDT 2025

**Completed:**
- Task 1.3: Configured basic bot (`main.py`, `app/config.py`).
- Task 1.4: Database Setup (Supabase PostgreSQL & Alembic).
    - Created `app/persistence/database.py` with SQLAlchemy async engine, session, and Base.
    - Configured `alembic.ini` with a placeholder URL.
    - Configured `alembic/env.py` for asynchronous migrations, using `ConfigService` for DB URL and `Base.metadata` for models.

**Next Steps:**
- Task 1.5: Implement `/start` and `/help` Commands.

## Tue May 13 23:17:36 PDT 2025

**Completed:**
- Set up Python virtual environment
- Created and populated requirements.txt with all necessary dependencies
- Installed all dependencies
- Configured environment variables in .env file with bot token, database connection, admin IDs, and target channel ID

**Next Steps:**
- Task 1.3: Configure basic bot (main.py, app/config.py)
- Task 1.4: Set up PostgreSQL database with Alembic

## Sat May 17 22:10:15 PDT 2025

**Completed:**
- Task 6.3: Enhance URL Content Extraction.
    - Integrated `crawl4ai` into `ContextService._fetch_content_from_url`.
    - Added `crawl4ai` to `requirements.txt`.
    - Configured `AsyncWebCrawler` with `BrowserConfig(java_script_enabled=True, headless=True)` and `CrawlerRunConfig(markdown_generator=DefaultMarkdownGenerator(content_filter=PruningContentFilter(...)), wait_until="networkidle")`.
    - This setup successfully fetches and processes dynamically loaded content from URLs, resolving issues where only minimal content (like a single newline) was previously extracted.
- Updated `memory-bank/techContext.md` to include `crawl4ai` under a new "Web Content Extraction" section.

**Learnings & Fixes:**
- `crawl4ai`'s default behavior or simple configurations might not be sufficient for all websites, especially those heavily reliant on JavaScript for content rendering.
- Iterative testing with different `crawl4ai` configurations (`headless` mode, `java_script_enabled`, `wait_for` with JS conditions, `wait_until="networkidle"`, and using `DefaultMarkdownGenerator` with `PruningContentFilter`) was necessary to find a robust solution.
- The `wait_until="networkidle"` option in `CrawlerRunConfig` proved effective for ensuring dynamic content is loaded before extraction.
- Discrepancies in behavior between a standalone test script and the integrated bot environment can occur, often related to browser automation initialization or JavaScript execution contexts.

**Next Steps:**
- Proceed to Phase 7 tasks, starting with Task 7.1: Implement `/my_votes` Command.
