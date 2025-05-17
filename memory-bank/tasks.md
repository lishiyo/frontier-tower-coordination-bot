# CoordinationBot Implementation Tasks

This document breaks down the implementation of CoordinationBot into manageable subtasks, phase by phase, with to-do lists and identified dependencies.

## Phase 1: Project Foundation & Basic Bot Setup

**Goal:** Establish the core project structure, environment, database, and basic bot connectivity.

**Dependencies:** None (Initial Phase)

**Subtasks:**

1.  **Task 1.1: Setup Project Structure & Version Control**
    *   [x] Create main project directory (`telegram_bot/`).
    *   [x] Initialize Git repository (`git init`).
    *   [x] Create initial directory structure as outlined in `systemPatterns.md` (e.g., `app/`, `tests/`, `alembic/`).
    *   [x] Create `.gitignore` file (add `.env`, `__pycache__/`, `*.db` if SQLite were used, etc.).
    *   [x] Create `README.md` (basic project description).
    *   [x] Create `systemPatterns.md` (already done).
    *   [x] Create `bot_commands.md` (already done).
    *   [x] Create this `tasks.md` file (already done).

2.  **Task 1.2: Setup Python Environment & Dependencies**
    *   [x] Create and activate a Python virtual environment (e.g., using `venv`).
    *   [x] Create `requirements.txt`.
    *   [x] Add initial core dependencies to `requirements.txt`:
        *   [x] `python-telegram-bot`
        *   [x] `SQLAlchemy`
        *   [x] `asyncpg` (for PostgreSQL)
        *   [x] `alembic`
        *   [x] `psycopg2-binary` (often needed for Alembic with PostgreSQL, even with asyncpg for runtime)
        *   [x] `python-dotenv`
        *   [x] `pylint`
        *   [x] `pytest`
        *   [x] `openai`
        *   [x] `chromadb`
        *   [x] `APScheduler`
    *   [x] Install dependencies (`pip install -r requirements.txt`).

3.  **Task 1.3: Configure Basic Bot (`main.py`, `app/config.py`)**
    *   [x] Create `app/config.py` to load settings from environment variables (`.env` file).
        *   [x] Load `TELEGRAM_BOT_TOKEN`.
        *   [x] Load `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`.
        *   [x] Load `OPENAI_API_KEY`.
        *   [x] Load `ADMIN_TELEGRAM_IDS` (comma-separated string).
        *   [x] Load `TARGET_CHANNEL_ID`.
    *   [x] Create `.env.example` with placeholder values.
    *   [x] Create `.env` file locally (and add to `.gitignore`).
    *   [x] Create `main.py` as the bot entry point.
        *   [x] Initialize `ConfigService`.
        *   [x] Initialize `python-telegram-bot.Application` with the bot token.

4.  **Task 1.4: Database Setup (Supabase PostgreSQL & Alembic)**
    *   [x] Create a new project in Supabase.
    *   [x] From the Supabase PostgreSQL connection string, extract the component parts (host, port, user, password, database name).
    *   [x] Update your `.env` file with these component parts for the variables: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, and `POSTGRES_DB`.
    *   [x] Initialize Alembic (`alembic init alembic`) if not already done.
    *   [x] Configure `alembic/env.py` for PostgreSQL and asynchronous context (target metadata for models). Ensure it uses the database URL constructed in `ConfigService`.
    *   [x] Configure `alembic.ini` with a placeholder `sqlalchemy.url` (the actual connection details will be loaded dynamically from `ConfigService` in `env.py`).
    *   [x] Implement `app/persistence/database.py`:
        *   [x] Setup asynchronous SQLAlchemy engine (`create_async_engine`) using the database URL from `ConfigService`.
        *   [x] Define `AsyncSessionLocal` for database sessions.
        *   [x] Define `Base` for declarative models (`declarative_base`).

5.  **Task 1.5: Implement `/start` and `/help` Commands**
    *   [x] Create `app/telegram_handlers/command_handlers.py`.
    *   [x] Implement `start_command` handler function.
        *   [x] Send a welcome message.
    *   [x] Implement `help_command` handler function.
        *   [x] Send a message listing basic commands (initially just `/start`, `/help`).
    *   [x] Register these handlers in `main.py`.
    *   [x] Test bot connection and these basic commands.

## Phase 2: User Management and Core Proposal Features (Static)

**Goal:** Implement user registration and the fundamental ability to create and store proposals (without conversational flow or advanced features yet).

**Dependencies:** Phase 1

**Subtasks:**

1.  **Task 2.1: User Model & Repository**
    *   [x] Define `User` SQLAlchemy model in `app/persistence/models/user_model.py` (id, telegram_id, username, first_name, last_updated).
    *   [x] Create `app/persistence/repositories/user_repository.py`.
        *   [x] Implement `get_or_create_user(telegram_id, username, first_name)` function.
    *   [x] Generate initial Alembic migration for the `User` table (`alembic revision -m "create_user_table"`) and apply it (`alembic upgrade head`).

2.  **Task 2.2: Implicit User Registration**
    *   [x] Create `app/core/user_service.py`.
        *   [x] Implement `register_user_interaction(telegram_id, username, first_name)` that calls the repository.
    *   [x] Modify `start_command` (and other relevant future handlers) to call `UserService.register_user_interaction` on first contact.

3.  **Task 2.3: Proposal Model & Repository**
    *   [x] Define `Proposal` SQLAlchemy model in `app/persistence/models/proposal_model.py` (id, proposer_id, title, description, proposal_type, options (JSON), channel_message_id, creation_date, deadline_date, status, outcome, raw_results).
    *   [x] Create `app/persistence/repositories/proposal_repository.py`.
        *   [x] Implement `add_proposal(proposer_id, title, ...)` function.
        *   [x] Implement `get_proposal_by_id(proposal_id)` function.
        *   [x] Implement `update_proposal_message_id(proposal_id, message_id)`.
    *   [x] Generate Alembic migration for `Proposal` table and apply.

4.  **Task 2.4: Basic `/propose` Command (Static Duration for now)**
    *   [x] In `app/telegram_handlers/command_handlers.py`, implement initial `propose_command` handler.
        *   [x] Parse title, description, options/FREEFORM.
        *   [x] For now, use a fixed/static duration to calculate `deadline_date` (e.g., 7 days from now). Conversational duration comes later.
        *   [x] Get `proposer_id` from the update.
        *   [x] For now, use the configured `TARGET_CHANNEL_ID` (from env variable) as the `target_channel_id`. Multi-channel support will be added later.
    *   [x] Create `app/core/proposal_service.py`.
        *   [x] Implement `create_proposal(proposer_id, title, description, proposal_type, options, deadline_date, target_channel_id)` function.
            *   [x] Call `UserRepository` to ensure proposer exists.
            *   [x] Call `ProposalRepository.add_proposal(...)`.
            *   [x] Return created proposal object or ID.
    *   [x] `propose_command` calls `ProposalService.create_proposal(...)`.
    *   [x] Send confirmation DM to proposer.
    *   [x] Post a basic proposal message to the specified `target_channel_id`.
        *   [x] Create `app/utils/telegram_utils.py` for formatting messages.
        *   [x] Ensure message for "free_form" proposals clearly displays Proposal ID and includes an inline button ("💬 Submit Your Idea") using `switch_inline_query_current_chat` to prefill the `/submit <proposal_id>` command.
        *   [x] Ensure message for "multiple_choice" proposals will later include inline keyboard for options (Task 4.2).
        *   [x] Store `channel_message_id` by calling `ProposalRepository.update_proposal_message_id(...)`.

5.  **Task 2.5: Add Multi-Channel Support to Proposal Model**
    *   [x] Update the `Proposal` SQLAlchemy model in `app/persistence/models/proposal_model.py` to add the `target_channel_id` field.
    *   [x] Generate a new Alembic migration for adding this field to the existing `Proposal` table:
        *   [x] Run `alembic revision -m "add_target_channel_id_to_proposal"`.
        *   [x] Edit the generated migration file to add a new column `target_channel_id` with a default value of the current `TARGET_CHANNEL_ID` from config.
    *   [x] Apply the migration using `alembic upgrade head`. (User will do this part)
    *   [x] Update `app/persistence/repositories/proposal_repository.py` methods to handle the new field.
    *   [x] Update `app/core/proposal_service.py` to ensure it properly passes `target_channel_id` to repository methods.
    *   [x] Verify that existing proposal functionality works with the new field. (User will do this part)

## Phase 3: Conversational Proposal Creation & Initial Context

**Goal:** Enhance proposal creation with conversational flow for duration and initial context gathering, integrating LLM and Vector DB.

**Dependencies:** Phase 1 (Config for LLM/VectorDB), Phase 2 (User, Proposal models/services)

**Subtasks:**

1.  **Task 3.1: LLM Service Setup**
    *   [x] Create `app/services/llm_service.py`.
    *   [x] Implement `parse_natural_language_duration(text)` function using OpenAI API.
    *   [x] Implement `generate_embedding(text)` function using OpenAI API.
    *   [x] Implement `get_completion(prompt)` function using OpenAI API.

2.  **Task 3.2: VectorDB Service Setup & Document Model**
    *   [x] Define `Document` SQLAlchemy model in `app/persistence/models/document_model.py` (id, title, content_hash, source_url, upload_date, vector_ids (JSON), proposal_id (nullable FK)).
    *   [x] Generate Alembic migration for `Document` table and apply. (User confirmed applied)
    *   [x] Create `app/persistence/repositories/document_repository.py` with `add_document` method.
    *   [x] Create `app/services/vector_db_service.py`.
        *   [x] Initialize ChromaDB client.
        *   [x] Implement `store_embeddings(doc_id, text_chunks, embeddings)` function.
        *   [x] Implement `search_similar_chunks(query_embedding, proposal_id_filter, top_n)` function.

3.  **Task 3.3: Context Service Setup**
    *   [x] Create `app/core/context_service.py`.
    *   [x] Implement `process_and_store_document(content_text_or_url, source_type, title, proposal_id=None)`:
        *   [x] Fetch content if URL (using httpx, basic implementation).
        *   [x] Chunk text (helper in `app/utils/text_processing.py` - `simple_chunk_text` created).
        *   [x] Generate embeddings for chunks via `LLMService`.
        *   [x] Store document metadata in `DocumentRepository`.
        *   [x] Store embeddings in `VectorDBService` (linking to SQL Document ID, and updating SQL doc with vector IDs).

4.  **Task 3.4: ConversationHandler for `/propose`**
    *   [ ] Refactor `propose_command` in `app/telegram_handlers/command_handlers.py` to use `ConversationHandler`.
    *   [ ] Define states: `ASK_DURATION`, `ASK_CONTEXT`.
    *   [ ] Handler for `ASK_DURATION` state:
        *   [ ] Get user's natural language duration.
        *   [ ] Call `LLMService.parse_natural_language_duration()` to get `deadline_date`.
        *   [ ] Store in conversation context, transition to `ASK_CONTEXT`.
        *   [ ] Prompt user for initial context.
    *   [ ] Handler for `ASK_CONTEXT` state:
        *   [ ] Get user's context input (text/URL/"no").
        *   [ ] If context provided:
            *   [ ] Call `ContextService.process_and_store_document(...)`, linking to the `proposal_id` (which will be created momentarily).
        *   [ ] Collate all proposal data from conversation context.
        *   [ ] Call `ProposalService.create_proposal(...)` (as in Phase 2.4, but now with LLM-parsed duration).
        *   [ ] Update `Document` with `proposal_id` if initial context was added.
        *   [ ] Send confirmation DM (including "use `/add_proposal_context` for more" and the edit and cancel commands).
        *   [ ] Post proposal to channel (Phase 2.4 logic, ensuring free-form proposals get the "Submit Idea" button and multiple-choice proposals are ready for option buttons in Phase 4).
        *   [ ] End conversation.
    *   [ ] Add `app/telegram_handlers/conversation_defs.py` for state constants.
    *   [ ] Add necessary message handlers for `ConversationHandler` in `app/telegram_handlers/message_handlers.py`.
    *   [ ] Manually test that this is working.

## Phase 4: Voting and Submission Logic

**Goal:** Enable users to vote on multiple-choice proposals and submit responses to free-form proposals.

**Dependencies:** Phase 2 (Proposal creation and channel posting)

**Subtasks:**

1.  **Task 4.1: Submission Model & Repository**
    *   [ ] Define `Submission` SQLAlchemy model in `app/persistence/models/submission_model.py` (id, proposal_id, submitter_id, response_content, timestamp; unique constraint on proposal_id, submitter_id).
    *   [ ] Generate Alembic migration for `Submission` table and apply.
    *   [ ] Create `app/persistence/repositories/submission_repository.py`.
        *   [ ] Implement `add_or_update_submission(proposal_id, submitter_id, response_content)`.
        *   [ ] Implement `get_submissions_for_proposal(proposal_id)`.

2.  **Task 4.2: Multiple-Choice Voting (`CallbackQueryHandler`)**
    *   [ ] In `app/utils/telegram_utils.py`, add helper to create inline keyboard for proposal options (using `option_index` in callback data: `vote_[proposal_id]_[option_index]`).
    *   [ ] Modify `ProposalService.create_proposal` and channel posting logic (specifically the part in Task 2.4 and Task 3.4 that posts to channel) to include this inline keyboard for "multiple_choice" types. Ensure this doesn't conflict with the "Submit Idea" button logic for free-form types.
    *   [ ] Create `app/telegram_handlers/callback_handlers.py`.
    *   [ ] Implement `handle_vote_callback` for `CallbackQueryHandler` matching `vote_.*`.
        *   [ ] Parse `proposal_id` and `option_index` from callback data.
        *   [ ] Get `user_id` (submitter_id).
    *   [ ] Create `app/core/submission_service.py`.
        *   [ ] Implement `record_vote(proposal_id, submitter_id, option_index)`:
            *   [ ] Call `ProposalRepository.get_proposal_by_id()`. Check if open & "multiple_choice".
            *   [ ] Get the actual option string from `proposal.options` using `option_index`.
            *   [ ] Call `UserRepository` to ensure voter exists.
            *   [ ] Call `SubmissionRepository.add_or_update_submission(...)` with the option string.
            *   [ ] Return success/failure.
    *   [ ] `handle_vote_callback` calls `SubmissionService.record_vote(...)`.
    *   [ ] Send ephemeral confirmation to user (`answer_callback_query`).

3.  **Task 4.3: Free-Form Submission (`/submit` Command)**
    *   [ ] In `app/telegram_handlers/command_handlers.py`, implement `submit_command` handler.
        *   [ ] Parse `proposal_id` and `<text_submission>`.
        *   [ ] Get `user_id` (submitter_id).
    *   [ ] In `app/core/submission_service.py`, implement `record_free_form_submission(proposal_id, submitter_id, text_submission)`:
        *   [ ] Call `ProposalRepository.get_proposal_by_id()`. Check if open & "free_form".
        *   [ ] Call `UserRepository` to ensure submitter exists.
        *   [ ] Call `SubmissionRepository.add_or_update_submission(...)`.
        *   [ ] Return success/failure.
    *   [ ] `submit_command` calls `SubmissionService.record_free_form_submission(...)`.
    *   [ ] Send DM confirmation to user.

## Phase 5: Deadline Management & Results Announcement

**Goal:** Implement scheduler for deadlines, process results (including LLM clustering), and announce them.

**Dependencies:** Phase 4 (Submissions data), Phase 3 (LLM service for clustering)

**Subtasks:**

1.  **Task 5.1: Scheduling Service Setup**
    *   [ ] Create `app/services/scheduling_service.py`.
    *   [ ] Initialize `AsyncIOScheduler` from `APScheduler`.
    *   [ ] Add function to start the scheduler (called from `main.py`).

2.  **Task 5.2: Deadline Checking Job**
    *   [ ] In `ProposalRepository`, add `find_expired_open_proposals()`.
    *   [ ] In `ProposalService`, implement `process_expired_proposals()`:
        *   [ ] Fetch expired open proposals using `ProposalRepository`.
        *   [ ] For each proposal:
            *   [ ] Update `proposal.status` to "closed" via `ProposalRepository`.
            *   [ ] **If "multiple_choice":**
                *   [ ] Get submissions via `SubmissionRepository.get_submissions_for_proposal()`.
                *   [ ] Tally votes. Determine outcome (winner/tie).
                *   [ ] Store outcome and raw_results (vote counts) in `Proposal` table via `ProposalRepository`.
            *   [ ] **If "free_form":**
                *   [ ] Get submissions via `SubmissionRepository.get_submissions_for_proposal()`.
                *   [ ] Call `LLMService.cluster_and_summarize_texts([sub.response_content for sub in submissions])` (needs implementation in `LLMService`).
                *   [ ] Store summary as `proposal.outcome` and full list of submissions in `proposal.raw_results` via `ProposalRepository`.
            *   [ ] Format results message (using `TelegramUtils`).
            *   [ ] Post results to the proposal's `target_channel_id` (using `channel_message_id` from `Proposal` to reply to or edit the original message).
    *   [ ] In `SchedulingService`, define `check_proposal_deadlines_job` that calls `ProposalService.process_expired_proposals()`.
    *   [ ] Add this job to the scheduler (e.g., to run every few minutes).

3.  **Task 5.3: Implement LLM Clustering for Free-Form**
    *   [ ] In `LLMService`, implement `cluster_and_summarize_texts(texts: list[str])`:
        *   [ ] May involve embedding all texts.
        *   [ ] Using an LLM prompt to group similar texts and provide a concise summary for each group/cluster.
        *   [ ] Return the summary text.

## Phase 6: RAG for `/ask` Command & Admin Document Management

**Goal:** Implement `/ask` command using RAG and admin document upload.

**Dependencies:** Phase 1 (VectorDB setup), Phase 3 (ContextService, LLMService, VectorDBService)

**Subtasks:**

1.  **Task 6.1: Implement `/ask` Command**
    *   [ ] In `app/telegram_handlers/command_handlers.py`, implement `ask_command` handler.
        *   [ ] Parse `question` and optional `proposal_id`.
    *   [ ] In `ContextService`, implement `get_answer_for_question(question_text, proposal_id_filter=None)`:
        *   [ ] Generate embedding for `question_text` via `LLMService`.
        *   [ ] Search for similar chunks in `VectorDBService`, passing `proposal_id_filter` if provided.
        *   [ ] Retrieve full text of relevant chunks (e.g., from `DocumentRepository` or if `VectorDBService` stores it).
        *   [ ] Construct prompt for LLM with context + question.
        *   [ ] Get answer via `LLMService.get_completion()`.
        *   [ ] Format answer, citing sources/snippets.
    *   [ ] `ask_command` calls `ContextService.get_answer_for_question()` and DMs response.

2.  **Task 6.2: Implement `/add_doc` Admin Command**
    *   [ ] In `app/telegram_handlers/command_handlers.py`, implement `add_doc_command` handler.
        *   [ ] Check if user is an admin (loaded from `ConfigService`).
        *   [ ] Parse URL or pasted text.
    *   [ ] `add_doc_command` calls `ContextService.process_and_store_document(content, source_type="admin_upload", title=...)`.
    *   [ ] Send confirmation to admin.

## Phase 7: User History, Proposal Management Commands & Privacy

**Goal:** Add commands for user history, proposal viewing/management, and privacy policy.

**Dependencies:** Phase 2 (Proposals), Phase 4 (Submissions), Phase 3 (ContextService for `/add_proposal_context`)

**Subtasks:**

1.  **Task 7.1: Implement `/my_votes` Command**
    *   [ ] In `SubmissionRepository`, add `get_submissions_by_user(submitter_id)`.
    *   [ ] In `ProposalRepository`, add `get_proposals_by_ids(list_of_proposal_ids)`.
    *   [ ] In `SubmissionService`, implement `get_user_submission_history(submitter_id)`:
        *   [ ] Get all user submissions.
        *   [ ] For each submission, fetch proposal details.
        *   [ ] Format a list of (proposal title, user's response, proposal status/outcome).
    *   [ ] In `app/telegram_handlers/command_handlers.py`, implement `my_votes_command` calling `SubmissionService.get_user_submission_history()` and DMs the result.

2.  **Task 7.2: Implement `/proposals open` and `/proposals closed`**
    *   [ ] In `ProposalRepository`, add `get_proposals_by_status(status: str)`.
    *   [ ] In `ProposalService`, implement `list_proposals_by_status(status: str)`:
        *   [ ] Fetch proposals from repository.
        *   [ ] Format list of (title, deadline/outcome).
    *   [ ] Implement `proposals_open_command` and `proposals_closed_command` in `command_handlers.py`, calling the service and DMing results.

3.  **Task 7.3: Implement `/edit_proposal` Command (Proposer Only)**
    *   [ ] In `SubmissionRepository`, add `count_submissions_for_proposal(proposal_id)`.
    *   [ ] In `ProposalService`, implement `edit_proposal_details(proposal_id, proposer_id, new_title, new_description, new_options)`:
        *   [ ] Fetch proposal. Verify `proposer_id` matches.
        *   [ ] Check `SubmissionRepository.count_submissions_for_proposal()`. If > 0, reject edit.
        *   [ ] Update proposal fields in `ProposalRepository`.
        *   [ ] If proposal message exists in channel, update it (using `TelegramUtils` and `bot.edit_message_text`).
    *   [ ] Implement `edit_proposal_command` in `command_handlers.py` (likely needs a conversation to get new details).

4.  **Task 7.4: Implement `/cancel_proposal` Command (Proposer Only)**
    *   [ ] In `ProposalService`, implement `cancel_proposal_by_proposer(proposal_id, proposer_id)`:
        *   [ ] Fetch proposal. Verify `proposer_id` matches and status is "open".
        *   [ ] Update status to "cancelled" via `ProposalRepository`.
        *   [ ] Update channel message (e.g., "Proposal cancelled").
    *   [ ] Implement `cancel_proposal_command` in `command_handlers.py`.

5.  **Task 7.5: Implement `/add_proposal_context` Command (Proposer Only)**
    *   [ ] In `ProposalRepository`, ensure `get_proposal_by_id` fetches `proposer_id`.
    *   [ ] Implement `add_proposal_context_command` in `command_handlers.py`:
        *   [ ] Parse `proposal_id`.
        *   [ ] Verify user is the proposer of `proposal_id`.
        *   [ ] If text/URL provided in command, call `ContextService.process_and_store_document(content, proposal_id=proposal_id, source_type="proposer_added_context")`.
        *   [ ] (Optional) Could initiate a short conversation if no context provided in command.
    *   [ ] Send confirmation/error DM.

6.  **Task 7.6: Implement `/view_submissions` Command**
    *   [ ] In `ProposalService`, implement `get_all_submissions_for_proposal_view(proposal_id)`:
        *   [ ] Fetch proposal. Ensure it's "closed" and "free_form".
        *   [ ] Fetch `proposal.raw_results` (which should contain the list of anonymized submissions).
        *   [ ] Format for display.
    *   [ ] Implement `view_submissions_command` in `command_handlers.py`.

7.  **Task 7.7: Implement `/privacy` Command**
    *   [ ] Create a static privacy policy text.
    *   [ ] Implement `privacy_command` in `command_handlers.py` to send this text.

8.  **Task 8.8: (Future) Multi-Channel Proposal System Implementation**
    *   [ ] Expand `ConfigService` to manage a list of authorized proposal channels beyond the default `TARGET_CHANNEL_ID`.
    *   [ ] Create a new model and repository for `AuthorizedChannel` if needed, or implement a configuration-based approach.
    *   [ ] Update the `ConversationHandler` for `/propose` to include channel selection flow when in multi-channel mode (new `ASK_CHANNEL` state).
    *   [ ] Implement logic to detect in-channel `/propose` commands, verify channel authorization, and set that channel as the proposal's `target_channel_id`.
    *   [ ] Update the channel results posting logic in `SchedulingService`/`ProposalService` to use the proposal's `target_channel_id` instead of a global channel ID.
    *   [ ] Add commands to manage authorized channels (admin only).
    *   [ ] Update user-facing proposal listings to include channel information.

## Phase 8: Comprehensive Testing, Refinement, and Deployment Preparation

**Goal:** Ensure bot stability, reliability, and user-friendliness; prepare for deployment.

**Dependencies:** All previous phases.

**Subtasks:**

1.  **Task 8.1: Unit & Integration Testing (`pytest`)**
    *   [ ] Write unit tests for all core service methods.
    *   [ ] Write unit tests for repository methods (can use in-memory SQLite for some if PostgreSQL is complex to mock, or mock DB session).
    *   [ ] Write unit tests for utility functions.
    *   [ ] Write integration tests for key flows (e.g., proposal creation -> voting -> results).
    *   [ ] Setup `tests/conftest.py` for fixtures (e.g., mock bot, mock db session).

2.  **Task 8.2: Linters and Code Quality Checks**
    *   [ ] Run `pylint` regularly and address issues.
    *   [ ] Ensure consistent code formatting.

3.  **Task 8.3: End-to-End Testing**
    *   [ ] Manually test all commands and user flows as described in `projectbrief.md` testing plan.
    *   [ ] Test with multiple users if possible.
    *   [ ] Test edge cases and error conditions.

4.  **Task 8.4: Logging and Error Handling Refinement**
    *   [ ] Review all logging statements for clarity and usefulness.
    *   [ ] Ensure all user-facing errors are handled gracefully and provide helpful messages.
    *   [ ] Implement more specific custom exceptions where appropriate.

5.  **Task 8.5: Configuration for Production**
    *   [ ] Finalize `.env.example` for production environment variables.
    *   [ ] Prepare deployment scripts/Dockerfile if containerizing.

6.  **Task 8.6: Documentation Review**
    *   [ ] Review `README.md` for setup and usage instructions.
    *   [ ] Ensure all major code components have docstrings.

7.  **Task 8.7: (Future) Admin Access to Voter Info (Post-Closure)**
    *   [ ] Design how admins access this (e.g., a new admin command `/view_proposal_voters <proposal_id>`).
    *   [ ] Implement necessary service and repository methods.
    *   [ ] Ensure clear logging of this access.

This detailed breakdown should provide a solid roadmap for implementation.
