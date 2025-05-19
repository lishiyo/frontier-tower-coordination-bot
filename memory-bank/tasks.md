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
    *   [x] Refactor/Implement `propose_command` in `app/telegram_handlers/command_handlers.py` as the entry point for a `ConversationHandler`.
        *   [x] Parse initial user input from `/propose [Initial Information]`.
        *   [x] Store any provided details (title, description, options/type) in `context.user_data`.
        *   [x] Determine the first state based on missing information.
    *   [x] Define states in `app/telegram_handlers/conversation_defs.py`: `COLLECT_TITLE`, `COLLECT_DESCRIPTION`, `COLLECT_PROPOSAL_TYPE`, `COLLECT_OPTIONS`, `ASK_CHANNEL` (if multi-channel), `ASK_DURATION`, `ASK_CONTEXT`.
    *   [x] Implement handlers in `app/telegram_handlers/message_handlers.py` for new states:
        *   [x] Handler for `COLLECT_TITLE` state:
            *   [x] Get title from user, store in `context.user_data`.
            *   [x] Transition to `COLLECT_DESCRIPTION`. Prompt user.
        *   [x] Handler for `COLLECT_DESCRIPTION` state:
            *   [x] Get description from user, store in `context.user_data`.
            *   [x] Transition to `COLLECT_PROPOSAL_TYPE`. Prompt user.
        *   [x] Handler for `COLLECT_PROPOSAL_TYPE` state (now in `callback_handlers.py`, handles inline and text):
            *   [x] Get proposal type from user. Store in `context.user_data`.
            *   [x] Transition to `COLLECT_OPTIONS` (if MC) or `ASK_DURATION` (if FF). Prompt user.
        *   [x] Handler for `COLLECT_OPTIONS` state:
            *   [x] Get options string from user. Parse options. Store in `context.user_data`.
            *   [x] Transition to `ASK_DURATION`. Prompt user.
    *   [x] Implement/Update handler for `ASK_DURATION` state:
        *   [x] Get user's natural language duration.
        *   [x] Call `LLMService.parse_natural_language_duration()` to get `deadline_date`.
        *   [x] Store `deadline_date` in `context.user_data`.
        *   [x] Transition to `ASK_CONTEXT`. Prompt user for initial context.
    *   [x] Implement/Update handler for `ASK_CONTEXT` state:
        *   [x] Get user's context input (text/URL/"no").
        *   [x] If context provided:
            *   [x] Call `ContextService.process_and_store_document(...)`, storing returned `document_id` in `context.user_data`.
        *   [x] Collate all proposal data from `context.user_data`.
        *   [x] Call `ProposalService.create_proposal(...)`.
        *   [x] If a context document was created, update its `proposal_id` field with the new proposal's ID via `DocumentRepository`.
        *   [x] Send confirmation DM (including "use `/add_doc` for more" and the edit and cancel commands).
        *   [x] Post proposal to the `target_channel_id` (retrieved from context).
        *   [x] End conversation.
    *   [x] Ensure all necessary message handlers, command handlers (entry point), and callback query handlers (for proposal type selection) are correctly registered with the `ConversationHandler` and the main application dispatcher.
    *   [ ] Manually test the full conversational flow for various inputs:
        *   [x] `/propose` (empty)
        *   [x] `/propose <Title only>`
        *   [x] `/propose <Title>; <Description>; <Options>`
        *   [x] `/propose <Title>; <Description>; FREEFORM`
        *   [x] Test with and without providing initial context.
        *   [x] Test cancellation at various stages.
    *   [x] **Follow-up Task:** Refactor repository methods in `DocumentRepository` (`add_document` and `link_document_to_proposal`) to not commit, ensuring the `handle_ask_context` handler manages the entire transaction.

3.  **Task 3.5: Implement Document Storage with Full Content and Basic Viewing Commands (Single-Channel)**
    *   [x] **Schema Change:**
        *   [x] Add `raw_content (Text, nullable=True)` field to `app/persistence/models/document_model.py`.
        *   [x] Generate Alembic migration for adding `raw_content` to `documents` table (`alembic revision -m "add_raw_content_to_documents"`) and apply it (`alembic upgrade head`).
    *   [x] **Update Document Ingestion:**
        *   [x] Modify `ContextService.process_and_store_document` to save the fetched/provided text into the new `raw_content` field of the `Document` object before saving to the database via `DocumentRepository.add_document`.
    *   [x] **Implement `/view_doc <document_id>` Command:**
        *   [x] In `app/persistence/repositories/document_repository.py`, add `get_document_by_id(document_id)` method that fetches a `Document` by its ID, including the `raw_content`.
        *   [x] In `app/core/context_service.py`, add `get_document_content(document_id)` method that calls `DocumentRepository.get_document_by_id()` and returns `document.raw_content`.
        *   [x] In `app/telegram_handlers/command_handlers.py`, implement `view_document_content_command` that takes `<document_id>`, calls `ContextService.get_document_content()`, and DMs the content to the user (handle potential long messages).
    *   [x] **Implement `/view_docs` (no arguments - Single Channel Behavior):**
        *   [x] In `app/telegram_handlers/command_handlers.py`, implement the base `view_docs_command` (handling no arguments).
        *   [x] This handler should retrieve the `TARGET_CHANNEL_ID` from `ConfigService`.
        *   [x] Format and DM a message to the user indicating this is the current proposal channel (e.g., "Proposals are currently managed in channel: [Channel ID/Name if available]").
    *   [x] **Implement `/view_docs <channel_id>` (Single Channel Behavior):**
        *   [x] In `app/persistence/repositories/proposal_repository.py`, add `get_proposals_by_channel_id(channel_id)` method.
        *   [x] In `app/core/proposal_service.py`, add `list_proposals_by_channel(channel_id)` that calls the new repository method and formats a list of proposals (ID, title, status).
        *   [x] Modify `view_docs_command` in `command_handlers.py` to handle the `<channel_id>` argument.
        *   [x] If `<channel_id>` is provided, it should call `ProposalService.list_proposals_by_channel()`. (Initially, this will only meaningfully work if the provided ID matches `TARGET_CHANNEL_ID`).
        *   [x] DM the list of proposals to the user.
    *   [x] **Implement `/view_docs <proposal_id>`:**
        *   [x] In `app/persistence/repositories/document_repository.py`, add `get_documents_by_proposal_id(proposal_id)` method.
        *   [x] In `app/core/context_service.py`, add `list_documents_for_proposal(proposal_id)` that calls the new repository method and formats a list of documents (ID, title).
        *   [x] Modify `view_docs_command` in `command_handlers.py` to handle the `<proposal_id>` argument.
        *   [x] If `<proposal_id>` is provided, it should call `ContextService.list_documents_for_proposal()`.
        *   [x] DM the list of documents to the user.
    *   [x] **Command Registration:** Ensure all new `/view_docs` and `/view_doc` handlers are registered in `main.py`.
    *   [x] **Refactor Command Handlers (Task 3.5.1):**
        *   [x] Create new files in `app/telegram_handlers/` for different command categories (e.g., `document_commands.py`, `proposal_commands.py`, `submission_commands.py`).
        *   [x] Move relevant command handler functions from `command_handlers.py` to these new files.
        *   [x] Keep `command_handlers.py` for shared logic, core commands.
        *   [x] Update imports in `main.py` to reflect the new locations of command handlers and register them accordingly.
    *   [x] **Testing (Single Channel):**
        *   [x] Test adding documents with context and ensure `raw_content` is stored.
        *   [x] Test `/view_doc <document_id>` to see content.
        *   [x] Test `/view_docs` (no args) shows the target channel.
        *   [x] Test `/view_docs <target_channel_id>` lists proposals.
        *   [x] Test `/view_docs <proposal_id>` lists documents for that proposal.

4.  **Task 3.6: (Utility) Implement Viewing of Stored Document Chunks (Optional - for Debugging)**
    *   [x] In `VectorDBService`, add a method like `get_document_chunks(sql_document_id)` to retrieve all text chunks from ChromaDB associated with a given SQL document ID.
    *   [x] (Optional) Create a simple admin command or utility script that uses this service method to allow viewing of stored chunks for debugging or verification purposes. (Created `app/scripts/view_document_chunks.py`)


## Phase 4: Voting and Submission Logic

**Goal:** Enable users to vote on multiple-choice proposals and submit responses to free-form proposals.

**Dependencies:** Phase 2 (Proposal creation and channel posting)

**Subtasks:**

1.  **Task 4.1: Submission Model & Repository**
    *   [x] Define `Submission` SQLAlchemy model in `app/persistence/models/submission_model.py` (id, proposal_id, submitter_id, response_content, timestamp; unique constraint on proposal_id, submitter_id).
    *   [x] Generate Alembic migration for `Submission` table and apply.
    *   [x] Create `app/persistence/repositories/submission_repository.py`.
        *   [x] Implement `add_or_update_submission(proposal_id, submitter_id, response_content)`.
        *   [x] Implement `get_submissions_for_proposal(proposal_id)`.

2.  **Task 4.2: Multiple-Choice Voting (`CallbackQueryHandler`)**
    *   [x] In `app/utils/telegram_utils.py`, add helper to create inline keyboard for proposal options (using `option_index` in callback data: `vote_[proposal_id]_[option_index]`).
    *   [x] Modify `ProposalService.create_proposal` and channel posting logic (specifically the part in Task 2.4 and Task 3.4 that posts to channel) to include this inline keyboard for "multiple_choice" types. Ensure this doesn't conflict with the "Submit Idea" button logic for free-form types.
    *   [x] Create `app/telegram_handlers/callback_handlers.py`.
    *   [x] Implement `handle_vote_callback` for `CallbackQueryHandler` matching `vote_.*`.
        *   [x] Parse `proposal_id` and `option_index` from callback data.
        *   [x] Get `user_id` (submitter_id).
    *   [x] Create `app/core/submission_service.py`.
        *   [x] Implement `record_vote(proposal_id, submitter_id, option_index)`:
            *   [x] Call `ProposalRepository.get_proposal_by_id()`. Check if open & "multiple_choice".
            *   [x] Get the actual option string from `proposal.options` using `option_index`.
            *   [x] Call `UserRepository` to ensure voter exists.
            *   [x] Call `SubmissionRepository.add_or_update_submission(...)` with the option string.
            *   [x] Return success/failure.
    *   [x] `handle_vote_callback` calls `SubmissionService.record_vote(...)`.
    *   [x] Send ephemeral confirmation to user (`answer_callback_query`).
    *   [x] Test this is working manually.
    *   [x] **UI Update:** After a successful vote:
        *   [x] Modify `handle_vote_callback` in `app/telegram_handlers/callback_handlers.py`.
        *   [x] Instead of a default ephemeral message, use `query.answer(text=f"Your vote for '{VOTED_OPTION}' has been recorded!", show_alert=True)` for a more prominent, user-specific pop-up confirmation.
        *   [x] The original proposal message in the channel (with voting buttons) will remain unchanged for other users to vote.

3.  **Task 4.3: Free-Form Submission (`/submit` Command)**
    *   [x] In `app/telegram_handlers/command_handlers.py`, implement `submit_command` handler. (Moved to `submission_command_handlers.py`)
        *   [x] Parse `proposal_id` and `<text_submission>`.
        *   [x] Get `user_id` (submitter_id).
    *   [x] In `app/core/submission_service.py`, implement `record_free_form_submission(proposal_id, submitter_id, text_submission)`:
        *   [x] Call `ProposalRepository.get_proposal_by_id()`. Check if open & "free_form".
        *   [x] Call `UserRepository` to ensure submitter exists.
        *   [x] Call `SubmissionRepository.add_or_update_submission(...)`.
        *   [x] Return success/failure.
    *   [x] `submit_command` calls `SubmissionService.record_free_form_submission(...)`.
    *   [x] Send DM confirmation to user.
    *   [x] Verify this is working manually.
    *   [x] **UI Enhancement:** Add an inline button ("💬 Submit Your Idea") to free-form proposal messages in the channel. This button should use `switch_inline_query_current_chat` to prefill `/submit <proposal_id> ` in the user's DM with the bot. (Verified as already implemented in Task 2.4/3.4 via `telegram_utils.get_free_form_submit_button`)

## Phase 5: Deadline Management & Results Announcement

**Goal:** Implement scheduler for deadlines, process results (including LLM clustering), and announce them.

**Dependencies:** Phase 4 (Submissions data), Phase 3 (LLM service for clustering)

**Subtasks:**

1.  **Task 5.1: Scheduling Service Setup**
    *   [x] Create `app/services/scheduling_service.py`.
    *   [x] Initialize `AsyncIOScheduler` from `APScheduler`.
    *   [x] Add function to start the scheduler (called from `main.py`).
    *   [x] Add function to stop the scheduler (called from `main.py` on exit).
    *   [x] Update `main.py` to import and call scheduler start/stop functions.

2.  **Task 5.2: Deadline Checking Job**
    *   [x] In `ProposalRepository`, add `find_expired_open_proposals()`. (Verified exists)
    *   [x] In `ProposalService`, implement `process_expired_proposals()`:
        *   [x] Fetch expired open proposals using `ProposalRepository`.
        *   [x] For each proposal:
            *   [x] Update `proposal.status` to "closed" via `ProposalRepository` (combined with outcome update).
            *   [x] **If "multiple_choice":**
                *   [x] Get submissions via `SubmissionRepository.get_submissions_for_proposal()`.
                *   [x] Tally votes. Determine outcome (winner/tie).
                *   [x] Store outcome and raw_results (vote counts) in `Proposal` table via `ProposalRepository`.
            *   [x] **If "free_form":**
                *   [x] Get submissions via `SubmissionRepository.get_submissions_for_proposal()`.
                *   [x] Call `LLMService.cluster_and_summarize_texts([sub.response_content for sub in submissions])` (needs implementation in `LLMService`). (Placeholder implemented)
                *   [x] Store summary as `proposal.outcome` and full list of submissions in `proposal.raw_results` via `ProposalRepository`. (Placeholder summary stored)
            *   [x] Format results message (using `TelegramUtils` - basic formatting implemented directly).
            *   [x] Post results to the proposal's `target_channel_id` (using `channel_message_id` from `Proposal` to reply to or edit the original message).
    *   [x] In `SchedulingService`, define `check_proposal_deadlines_job` that calls `ProposalService.process_expired_proposals()`.
    *   [x] Add this job to the scheduler (e.g., to run every few minutes).
    *   [x] Ensure `ProposalService` has access to the bot application instance for sending messages.
    *   [x] Manually test.
    *   [x] Make everything PST instead of UTC (e.g. "Voting ends", "Deadline set for" should be in UTC).
    *   [x] For the results message, instead of "(DM the bot)" use "(DM @botname)".

3.  **Task 5.3: Implement LLM Clustering for Free-Form**
    *   [x] In `LLMService`, implement `cluster_and_summarize_texts(texts: list[str])`:
        *   [x] May involve embedding all texts.
        *   [x] Using an LLM prompt to group similar texts and provide a concise summary for each group/cluster.
        *   [x] Return the summary text.
        *   [x] Test this is working (should be displaying as results for free-form proposal results.)

## Phase 6: RAG for `/ask` Command & Admin Document Management

**Goal:** Implement `/ask` command using RAG and admin document upload.

**Dependencies:** Phase 1 (VectorDB setup), Phase 3 (ContextService, LLMService, VectorDBService)

**Subtasks:**

1.  **Task 6.1: Implement `/add_global_doc` Admin Command**
    *   [x] In `app/telegram_handlers/admin_command_handlers.py`, implement `add_global_doc_command` handler.
        *   [x] Check if user is an admin (loaded from `ConfigService`).
        *   [x] Parse URL or pasted text.
        *   [x] Prompt for a document title if not easily inferable.
        *   [x] Handle content provided directly with the command or in a follow-up message.
    *   [x] `add_global_doc_command` calls `ContextService.process_and_store_document(content, source_type="admin_global_text/url", title=user_provided_title, proposal_id=None)`.
        *   [x] Ensure `admin_command_handlers.py` instantiates services like `ContextService` internally with a proper session, rather than relying on a global `application.services` for session-dependent services.
    *   [x] Send confirmation to admin.

2.  **Task 6.2: Implement `/ask` Command**
    *   [x] In `app/telegram_handlers/command_handlers.py`, implement `ask_command` handler.
        *   [x] Parse `question` and optional `proposal_id`.
    *   [x] In `ContextService`, implement `get_answer_for_question(question_text, proposal_id_filter=None)`:
        *   [x] Generate embedding for `question_text` via `LLMService`.
        *   [x] Search for similar chunks in `VectorDBService`, passing `proposal_id_filter` if provided.
        *   [x] Retrieve full text of relevant chunks (e.g., from `DocumentRepository` or if `VectorDBService` stores it).
        *   [x] Construct prompt for LLM with context + question.
        *   [x] Get answer via `LLMService.get_completion()`.
        *   [x] Format answer, citing sources/snippets.
    *   [x] `ask_command` calls `ContextService.get_answer_for_question()` and DMs response.

3.  **Task 6.3: Enhance URL Content Extraction**
    *   [x] Research and select a robust HTML parsing/content extraction library or method (e.g., BeautifulSoup, trafilatura, crawl4ai, Firecrawl). crawl4ai preferred.
    *   [x] Implement the chosen solution within `ContextService._fetch_content_from_url` to replace the basic `response.text`.
        *   Used `crawl4ai` with `AsyncWebCrawler`.
        *   Configured `BrowserConfig` with `java_script_enabled=True`.
        *   Configured `CrawlerRunConfig` with `DefaultMarkdownGenerator`, `PruningContentFilter`, and `wait_until="networkidle"` to handle dynamic content and improve extraction quality.
    *   [x] Ensure the new implementation extracts clean, main content from web pages, stripping HTML tags, scripts, and other noise.
    *   [x] Test with various URLs to confirm improved context quality for RAG.

## Phase 7: User History, Proposal Management Commands & Privacy

**Goal:** Add commands for user history, proposal viewing/management, and privacy policy.

**Dependencies:** Phase 2 (Proposals), Phase 4 (Submissions), Phase 3 (ContextService for `/add_doc`)

**Subtasks:**

1.  **Task 7.1: Implement `/my_votes` Command**
    *   [x] In `SubmissionRepository`, add `get_submissions_by_user(submitter_id)`. (Verified exists)
    *   [x] In `ProposalRepository`, add `get_proposals_by_ids(list_of_proposal_ids)`. (Verified exists)
    *   [x] In `SubmissionService`, implement `get_user_submission_history(submitter_id)`:
        *   [x] Get all user submissions.
        *   [x] For each submission, fetch proposal details.
        *   [x] Format a list of (proposal title, user's response, proposal status/outcome).
    *   [x] In `app/telegram_handlers/command_handlers.py`, implement `my_votes_command` calling `SubmissionService.get_user_submission_history()` and DMs the result.
    *   [x] Write unit tests for the new repository and service methods, and the command handler.
    *   [x] Test this is working manually.

2.  **Task 7.2: Implement `/my_proposals` command**
    *   [x] In `app/persistence/repositories/proposal_repository.py`, add `get_proposals_by_proposer_id(proposer_telegram_id: int)`:
        *   [x] This method should retrieve all proposals where the `proposer_telegram_id` matches the given ID.
    *   [x] In `app/core/proposal_service.py`, add `list_proposals_by_proposer(user_id: int)`:
        *   [x] This service method will call `ProposalRepository.get_proposals_by_proposer_id()`.
        *   [x] It should format the results into a list suitable for display (e.g., list of dictionaries with proposal ID, title, status, deadline/outcome, target_channel_id).
        *   [x] Timestamps like `deadline_date` or `creation_date` should be formatted for display using `app.utils.telegram_utils.format_datetime_for_display`.
    *   [x] In `app/telegram_handlers/user_command_handlers.py` (or `proposal_command_handlers.py`), implement `my_proposals_command`:
        *   [x] This command handler will call `ProposalService.list_proposals_by_proposer()`.
        *   [x] It will format and send the list of proposals to the user via DM.
        *   [x] Ensure proper MarkdownV2 escaping for the message.
        *   [x] Handle potential message length limits if the list is very long (e.g., basic pagination or a note to the user).
        *   [x] If no proposals are found, it should inform the user (e.g., "You haven't created any proposals yet.").
    *   [x] Add `/my_proposals` command to `main.py` command registration.
    *   [x] Ensure `/my_proposals` is documented in `memory-bank/bot_commands.md`.
    *   [x] Write unit tests for the new repository and service methods, and the command handler.
    *   [x] Test this is working manually.

3.  **Task 7.3: Implement `/proposals`, `/proposals open` and `/proposals closed`**
    *   [x] If the user just types `/proposals`, the bot should ask "open or closed?" If the user says "open", use `/proposals open` and if closed, use `/proposals closed`.
    *   [x] In `ProposalRepository`, add `get_proposals_by_status(status: str)`.
    *   [x] In `ProposalService`, implement `list_proposals_by_status(status: str)`:
        *   [x] Fetch proposals from repository.
        *   [x] Format list of (title, deadline/outcome).
    *   [x] Implement `proposals_open_command` and `proposals_closed_command` in `proposal_command_handlers.py`, calling the service and DMing results.
    *   [x] Write unit tests, verify passing.
    *   [x] Test this is working manually.

4.  **Task 7.4: Implement `/edit_proposal` Command (Proposer Only)**
    *   [ ] If the user just says `/edit_proposal`, the bot should ask "which proposal? use `/my_proposals` to list all, then `/edit_proposal <proposal_id>`"; then show the button `/my_proposals`.
    *   [ ] In `SubmissionRepository`, add `count_submissions_for_proposal(proposal_id)`.
    *   [ ] In `ProposalService`, implement `edit_proposal_details(proposal_id, proposer_id, new_title, new_description, new_options)`:
        *   [ ] Fetch proposal. Verify `proposer_id` matches.
        *   [ ] Check `SubmissionRepository.count_submissions_for_proposal()`. If > 0, reject edit. Tell the user it is not possible to edit an already-created proposal, they have to cancel and make a new one.
        *   [ ] Update proposal fields in `ProposalRepository`.
        *   [ ] If proposal message exists in channel, update it (using `TelegramUtils` and `bot.edit_message_text`).
    *   [ ] Implement `edit_proposal_command` in `proposal_command_handlers.py` (likely needs a conversation to get new details). 
    *   [ ] Write unit tests, verify passing.
    *   [ ] Test this is working manually.

5.  **Task 7.5: Implement `/cancel_proposal` Command (Proposer Only)**
    *   [ ] If the user just says `/cancel_proposal`, the bot should ask "which proposal? use `/my_proposals` to list all, then `/cancel_proposal <proposal_id>`"; then show the button `/my_proposals`.
    *   [ ] In `ProposalService`, implement `cancel_proposal_by_proposer(proposal_id, proposer_id)`:
        *   [ ] Fetch proposal. Verify `proposer_id` matches and status is "open".
        *   [ ] Update status to "cancelled" via `ProposalRepository`.
        *   [ ] Update channel message (e.g., "Proposal cancelled").
    *   [ ] Implement `cancel_proposal_command` in `proposal_command_handlers.py`.
    *   [ ] Write unit tests, verify passing.
    *   [ ] Test this is working manually.

## Phase 8: Doc Management Commands

1. **Task 8.1: Implement `/my_docs` Command**
    *   [ ] In `app/persistence/repositories/document_repository.py`, add `get_documents_by_proposer_id(proposer_telegram_id: int)`:
        *   [ ] This method should retrieve documents linked to proposals created by the given `proposer_telegram_id` (i.e., documents where `document.proposal_id` links to a `proposal` whose `proposer_telegram_id` matches).
        *   [ ] This will require a join between the `documents` table and the `proposals` table on `proposal_id`.
    *   [ ] In `app/core/context_service.py`, add `list_documents_by_proposer(user_id: int)`:
        *   [ ] This service method will call `DocumentRepository.get_documents_by_proposer_id()`.
        *   [ ] It should format the results into a list of dictionaries, each containing `document_id`, `document_title`, and optionally the `proposal_id` and `proposal_title` it's associated with.
    *   [ ] In `app/telegram_handlers/user_command_handlers.py`, implement `my_docs_command`:
        *   [ ] This command handler will call `ContextService.list_documents_by_proposer()`.
        *   [ ] It will format and send the list of documents to the user via DM.
        *   [ ] If no documents are found, it should inform the user (e.g., "You haven't added any documents to your proposals yet.").
    *   [ ] Add `/my_docs` command to `main.py` command registration.
    *   [x] Ensure `/my_docs` is documented in `memory-bank/bot_commands.md`.
    *   [ ] Write unit tests for the new repository and service methods, and the command handler.
    *   [ ] Test this is working manually.

2. **Task 8.2: Implement `/add_doc` Command (Proposer Only)**
    *   [ ] If the user just says `/add_doc`, the bot should ask "which proposal? use `/my_proposals` to list all, then `/add_doc <doc_id>`"; then show the button for `/my_proposals`.
    *   [ ] In `ProposalRepository`, ensure `get_proposal_by_id` fetches `proposer_id`.
    *   [ ] Implement `add_doc_command` in `document_command_handlers.py`:
        *   [ ] Parse `proposal_id`.
        *   [ ] Verify user is the proposer of `proposal_id`.
        *   [ ] If text/URL provided in command, call `ContextService.process_and_store_document
        (content, proposal_id=proposal_id, source_type="proposer_added_context")`.
        *   [ ] (Optional) Could initiate a short conversation if no context provided in command.
    *   [ ] Send confirmation/error DM.
    *   [ ] Write unit tests, verify passing.
    *   [ ] Test this is working manually.

3.  **Task 8.3: Implement Proposer Document Editing and Deletion**
    *   **Implement `/edit_doc <document_id>` Command (Proposer Only):**
        *   [ ] If the user just says `/edit_doc`, the bot should ask "which doc? use `/my_docs` to list all, then `/edit_doc <doc_id>`"; then show the button for `/my_docs`.
        *   [ ] In `app/telegram_handlers/document_command_handlers.py` (or similar), implement `edit_doc_command`.
        *   [ ] Handler parses `document_id`.
        *   [ ] In `ContextService`, add `can_user_edit_document(user_id, document_id)`: 
            *   [ ] Fetches document, then its associated proposal, then proposal's `proposer_id`.
            *   [ ] Returns `True` if `user_id` matches `proposer_id` and document is linked to a proposal.
        *   [ ] Verify user is the proposer of the proposal linked to the document using `ContextService.can_user_edit_document()`.
        *   [ ] Initiate a conversation (or expect further message) to get the new document content (text or URL).
        *   [ ] In `ContextService`, add `update_document_content(document_id, new_content, new_title=None)`:
            *   [ ] Updates `raw_content` and `title` (if provided) in `DocumentRepository`.
            *   [ ] Re-chunks, re-embeds, and updates embeddings in `VectorDBService`.
            *   [ ] Updates `content_hash`.
        *   [ ] Call `ContextService.update_document_content()`.
        *   [ ] Send confirmation/error DM.
        *   [ ] Write unit tests, verify passing.
        *   [ ] Test this is working manually.
    *   **Implement `/delete_doc <document_id>` Command (Proposer Only):**
        *   [ ] If the user just says `/delete_doc`, the bot should ask "which doc? use `/my_docs` to list all, then `/delete_doc <doc_id>`"; then show the button for `/my_docs`.
        *   [ ] In `app/telegram_handlers/document_command_handlers.py` (or similar), implement `delete_doc_command`.
        *   [ ] Handler parses `document_id`.
        *   [ ] Use `ContextService.can_user_edit_document()` (or a similar `can_user_delete_document`) to verify proposer.
        *   [ ] In `ContextService`, add `delete_document(document_id)`:
            *   [ ] Removes associated embeddings from `VectorDBService`.
            *   [ ] Deletes document from `DocumentRepository`.
        *   [ ] Call `ContextService.delete_document()`.
        *   [ ] Send confirmation/error DM.
        *   [ ] Write unit tests, verify passing.
        *   [ ] Test this is working manually.

4.  **Task 8.4: Implement Admin Global Document Management (List, Edit, Delete)**
    *   **Implement `/view_global_docs` Command (Admin Only):**
        *   [ ] In `app/telegram_handlers/admin_command_handlers.py`, implement `view_global_docs_command`.
        *   [ ] Verify user is an admin.
        *   [ ] In `DocumentRepository`, add `get_global_documents()` (e.g., where `proposal_id` is NULL).
        *   [ ] In `ContextService`, add `list_global_documents()` that calls the repository method and formats a list (ID, title).
        *   [ ] DM the list to the admin.
        *   [ ] Test this is working manually.
    *   **Implement `/edit_global_doc <document_id>` Command (Admin Only):**
        *   [ ] If the admin just says `/edit_global_doc`, the bot should ask "which doc? use `/my_docs` to list all, then `/edit_global_doc <doc_id>`"; then show the button for `/my_docs`.
        *   [ ] In `app/telegram_handlers/admin_command_handlers.py`, implement `edit_global_doc_command`.
        *   [ ] Verify user is an admin.
        *   [ ] Handler parses `document_id`.
        *   [ ] In `ContextService`, add `is_global_document(document_id)` (checks if `proposal_id` is NULL).
        *   [ ] Verify document is a global document using `ContextService.is_global_document()`.
        *   [ ] Initiate a conversation (or expect further message) for new content/title.
        *   [ ] Call `ContextService.update_document_content()` (from Task 7.8).
        *   [ ] Send confirmation/error DM.
        *   [ ] Write unit tests, verify passing.
        *   [ ] Test this is working manually.
    *   **Implement `/delete_global_doc <document_id>` Command (Admin Only):**
        *   [ ] If the admin just says `/delete_global_doc`, the bot should ask "which doc? use `/my_docs` to list all, then `/delete_global_doc <doc_id>`"; then show the button for `/my_docs`.
        *   [ ] In `app/telegram_handlers/admin_command_handlers.py`, implement `delete_global_doc_command`.
        *   [ ] Verify user is an admin.
        *   [ ] Handler parses `document_id`.
        *   [ ] Verify document is a global document using `ContextService.is_global_document()`.
        *   [ ] Call `ContextService.delete_document()` (from Task 7.8).
        *   [ ] Send confirmation/error DM.
        *   [ ] Write unit tests, verify passing.
        *   [ ] Test this is working manually.

5.  **Task 8.5: Implement `/view_results` Command**
    *   [ ] If the user just says `/view_results`, the bot should ask "which proposal? use `/my_proposals` to list all your proposals, `/proposals open` for all open proposals, or `/proposals closed` for all closed proposals, then `/view_results <proposal_id>`". Show the buttons for `/my_proposals`, `/proposals open`, and `/proposals closed`.
    *   [ ] In `ProposalService`, implement `get_all_results_for_proposal_view(proposal_id)`:
        *   [ ] Fetch proposal. Ensure it's "closed".
        *   [ ] Free "multiple_choice" results, fetch the total vote counts for each of the options.
        *   [ ] For "free_form" results, fetch `proposal.raw_results` (which should contain the list of anonymized submissions).
        *   [ ] Format for display.
    *   [ ] Implement `view_results_command` in `submission_command_handlers.py`.
    *   [ ] Write unit tests, verify passing.
    *   [ ] Test this is working manually.

6.  **Task 8.6: Implement `/privacy` Command**
    *   [ ] Create a static privacy policy text.
    *   [ ] Implement `privacy_command` in `command_handlers.py` to send this text.
    *   [ ] Write unit tests, verify passing.
    *   [ ] Test this is working manually.


---

## Phase 9: Multi-Channel Support Enhancements

**Goal:** Extend multi-channel capabilities to proposal creation, listing, and context document viewing.

**Dependencies:** Initial multi-channel setup (from previous Phase 8 tasks if they exist, or core single-channel features). Core document viewing from Task 3.5.

**Subtasks:**

1.  **Task 9.1: Multi-Channel Proposal System Implementation (Core)**
    *   (This task might already exist or be partially done if Phase 8 was previously just about proposal multi-channel support. Adjust as needed.)
    *   [ ] Expand `ConfigService` to manage a list of authorized proposal channels beyond the default `TARGET_CHANNEL_ID`.
    *   [ ] Create a new model and repository for `AuthorizedChannel` (e.g., `app/persistence/models/authorized_channel_model.py` and `app/persistence/repositories/authorized_channel_repository.py`) if opting for DB-based management, or implement a purely configuration-based approach in `ConfigService`.
        *   [ ] Include fields like `channel_id` (PK), `channel_name` (optional).
        *   [ ] Add Alembic migration if model is created.
    *   [ ] Implement admin commands to add/list/remove authorized channels if using DB-based management.
    *   [ ] Update the `ConversationHandler` for `/propose` (`ASK_CHANNEL` state) to fetch and display these authorized channels when initiated via DM in multi-channel mode.
        *   [ ] Prompt user to select a channel.
        *   [ ] Store selected `target_channel_id` in `context.user_data`.
        *   [ ] Transition to `ASK_DURATION`. Prompt user.
    *   [ ] Implement logic to detect in-channel `/propose` commands, verify channel authorization against the configured list/table, and set that channel as the proposal's `target_channel_id`.
    *   [ ] Update the channel results posting logic in `SchedulingService`/`ProposalService` to use the proposal's `target_channel_id`.
    *   [ ] Update user-facing proposal listings (like `/proposals open/closed`) to potentially include channel information or allow filtering.
    *   [ ] Write unit tests, verify passing.

2.  **Task 9.2: Enhance `/view_docs` for Multi-Channel Support**
    *   [ ] **`/view_docs` (no arguments):**
        *   [ ] Modify handler to retrieve the list of *all* authorized channels from `ConfigService` (or `AuthorizedChannelRepository`).
        *   [ ] Format and DM this list (channel IDs and names if available) to the user.
    *   [ ] **`/view_docs <channel_id>`:**
        *   [ ] Ensure this command correctly lists proposals for *any* valid authorized `channel_id` (not just the old single `TARGET_CHANNEL_ID`). No significant change if `ProposalService.list_proposals_by_channel` already just takes a `channel_id`.
    *   [ ] **General Document Association (Future Consideration for RAG):**
        *   [ ] Consider if general documents (added via `/add_global_doc`) should be associable with specific authorized channels (new `associated_channel_id` field in `Document` model).
        *   [ ] If so, `/view_docs <channel_id>` could also list general documents associated with that channel.
        *   [ ] RAG queries via `/ask` could then also be filtered/prioritized by documents relevant to the channel a user is in or asking about.
        *   [ ] Write unit tests, verify passing.

3.  **Task 9.3: Testing Multi-Channel Document Viewing**
    *   [ ] Configure multiple authorized channels.
    *   [ ] Test `/view_docs` (no args) lists all configured channels.
    *   [ ] Test `/view_docs <channel_id>` for different authorized channels, ensuring correct proposal listings.
    *   [ ] Ensure `/view_docs <proposal_id>` and `/view_doc <document_id>` continue to function correctly regardless of how many channels are configured.
    *   [ ] Write unit tests, verify passing.

4.  **Task 9.4: Implement Intelligent Help via LLM (`/help <question>`)**
    *   **Goal:** Allow users to ask natural language questions about bot functionality using `/help <question>` and receive LLM-generated answers based on `bot_commands.md`.
    *   **Dependencies:** `LLMService` (Phase 3.1), `ContextService` (Phase 3.3, or a new dedicated `HelpService`), completed `bot_commands.md`.
    *   **Subtasks:**
        *   [ ] Modify `help_command` in `app/telegram_handlers/command_handlers.py`:
            *   [ ] If arguments are present after `/help`, capture them as the `question_text`.
            *   [ ] If `question_text` exists, call a new service method (e.g., `ContextService.get_intelligent_help(question_text)`).
            *   [ ] If no arguments, display the standard help message (list of commands).
        *   [ ] Implement `get_intelligent_help(question_text)` in `app/core/context_service.py` (or a new `HelpService`):
            *   [ ] Load the content of `memory-bank/bot_commands.md`.
            *   [ ] Call a new method in `LLMService` (e.g., `LLMService.answer_question_from_docs(question, docs_content)`) providing the user's question and the content of `bot_commands.md`.
            *   [ ] Return the LLM's formatted answer.
            *   [ ] If the LLM's answer includes commands, also include the commands as button options. For example user says "/help how do I make a proposal" the bot should say "Use the `/proposal` command and I'll walk you through step by step. Or use `/proposal <Title>; <description>; <option1>, <option2>` for multiple-choice (or `freeform` for freeform)." The "proposal" button should appear.
        *   [ ] Implement `answer_question_from_docs(question, docs_content)` in `app/services/llm_service.py`:
            *   [ ] Construct a prompt for the LLM that includes the `docs_content` and the user's `question`.
            *   [ ] The prompt should instruct the LLM to use the provided `docs_content` to answer the `question` by explaining relevant commands and their usage.
            *   [ ] Call the LLM completion endpoint and return the answer.
        *   [ ] Ensure the `help_command` handler sends the response from the service back to the user via DM.
        *   [ ] Write unit tests, verify passing.
        *   [ ] Test with various questions to ensure clarity and accuracy of LLM responses.

5.  **Task 9.5: Implement Enhanced `/ask` for Proposal Querying and `/my_vote` Command**
    *   **Goal:** Allow users to ask natural language questions about proposals via `/ask` (e.g., "what proposals closed last week?", "which proposals mentioned funding?") and view their specific vote/submission for an identified proposal via `/my_vote <proposal_id>`.
    *   **Strategy Document:** See `memory-bank/intelligentAsks.md`.
    *   **Dependencies:** `LLMService` (Phase 3.1), `VectorDBService` (Phase 3.2), `ProposalService`, `SubmissionService`, `ProposalRepository`, `SubmissionRepository`.
    *   **Subtasks:**
        *   **Subtask 9.5.1: Implement Proposal Content Indexing (Can be done earlier, e.g., alongside or after Phase 3/4)**
            *   [ ] In `app/services/vector_db_service.py`, implement `add_proposal_embedding(proposal_id: int, text_content: str, embedding: list[float], metadata: dict)`:
                *   [ ] This method should add/update the proposal's text and embedding in a new ChromaDB collection named `proposals_content` (or similar).
                *   [ ] The `metadata` should include `proposal_id`, `status`, `deadline_date_iso`, `creation_date_iso`, `type`, `target_channel_id`.
                *   [ ] Ensure the collection is created if it doesn't exist.
            *   [ ] In `app/core/proposal_service.py`, modify `create_proposal(...)` and `edit_proposal_details(...)`:
                *   [ ] After a proposal is successfully saved/updated in the SQL database:
                    *   [ ] Concatenate `proposal.title` and `proposal.description` to form `proposal_text_to_index`.
                    *   [ ] Call `LLMService.generate_embedding(proposal_text_to_index)`.
                    *   [ ] Call `VectorDBService.add_proposal_embedding(...)` with the necessary details.
            *   [ ] Write unit tests for the changes in `ProposalService` and `VectorDBService` related to proposal indexing.
            *   [ ] (Optional, Post-MVP) Consider creating a one-time script to backfill embeddings for existing proposals in the database.

        *   **Subtask 9.5.2: Implement Core `/ask` Enhancement Logic for Proposal Queries**
            *   [ ] In `app/services/llm_service.py`:
                *   [ ] Implement/Modify `analyze_ask_query(query_text: str) -> dict`.
                    *   [ ] Design prompt to determine primary intent (`query_proposals` or `query_general_docs`).
                    *   [ ] If `query_proposals`, extract `content_keywords` (for semantic search) and `structured_filters` (e.g., status, date_query, proposal_type).
                *   [ ] (If necessary) Enhance `parse_natural_language_duration(text: str)` to reliably parse date ranges or relative queries (e.g., "last month") into start/end datetimes for filtering.
            *   [ ] In `app/persistence/repositories/proposal_repository.py`:
                *   [ ] Implement `find_proposals_by_dynamic_criteria(status: Optional[str] = None, date_range: Optional[tuple[datetime, datetime]] = None, proposal_type: Optional[str] = None, creation_date_range: Optional[tuple[datetime, datetime]] = None) -> list[Proposal]`.
                    *   [ ] This method should construct and execute a dynamic SQLAlchemy query.
            *   [ ] In `app/services/vector_db_service.py`:
                *   [ ] Implement `search_proposal_embeddings(query_embedding: list[float], top_n: int = 5, filter_proposal_ids: Optional[list[int]] = None) -> list[dict]`.
                    *   [ ] This method searches the `proposals_content` collection.
                    *   [ ] It should return a list of results, each including at least `proposal_id` and `score`.
            *   [ ] In `app/core/context_service.py`:
                *   [ ] Implement/Refactor `handle_intelligent_ask(query_text: str, user_telegram_id: int) -> str` (this will be the main orchestrator for the `/ask` command logic):
                    *   [ ] Call `LLMService.analyze_ask_query(query_text)`.
                    *   [ ] If intent is `query_proposals`:
                        *   [ ] Perform date parsing for `structured_filters.date_query` (if any) using `LLMService`.
                        *   [ ] Perform structured filtering using `ProposalRepository.find_proposals_by_dynamic_criteria()`.
                        *   [ ] If `content_keywords` exist, generate their embedding and search using `VectorDBService.search_proposal_embeddings()`.
                        *   [ ] Consolidate proposal IDs from structured and semantic searches.
                        *   [ ] Fetch full `Proposal` objects for the final list of IDs using `ProposalRepository.get_proposals_by_ids()`.
                        *   [ ] Construct prompt for `LLMService.get_completion` to synthesize an answer. The answer should list matching proposals and guide the user to use `/my_vote <proposal_id>` to see their specific submission for any of these proposals.
                        *   [ ] Call `LLMService.get_completion()` to get the final answer string.
                    *   [ ] Else (intent is `query_general_docs` or fallback):
                        *   [ ] Proceed with the existing RAG flow for general documents.
            *   [ ] In `app/telegram_handlers/command_handlers.py` (or wherever `ask_command` is):
                *   [ ] Modify the `ask_command` handler to call `ContextService.handle_intelligent_ask(question_text, user_telegram_id)`.
            *   [ ] Write unit tests for all new/modified methods in `LLMService`, `ProposalRepository`, `VectorDBService`, and `ContextService` related to the enhanced `/ask` flow.

        *   **Subtask 9.5.3: Implement `/my_vote <proposal_id>` Command**
            *   [ ] In `app/persistence/repositories/submission_repository.py`:
                *   [ ] Implement `get_submission_by_proposal_and_user(proposal_id: int, submitter_id: int) -> Submission | None`.
            *   [ ] In `app/core/submission_service.py`:
                *   [ ] Implement `get_user_submission_for_proposal(user_id: int, proposal_id: int) -> str`:
                    *   [ ] Calls `ProposalRepository.get_proposal_by_id()` to get proposal details (e.g., title).
                    *   [ ] Calls `SubmissionRepository.get_submission_by_proposal_and_user()`.
                    *   [ ] Formats a response string (e.g., "For proposal '[Title]', your submission was: '[content]'" or "You did not make a submission for...").
            *   [ ] In `app/telegram_handlers/user_command_handlers.py` (or similar):
                *   [ ] Implement `my_vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE)`:
                    *   [ ] Parses `proposal_id` from command arguments.
                    *   [ ] If `proposal_id` is missing: Send a message asking "Which proposal? Use /my_vote <proposal_id>. You can see all open and closed proposals for their IDs." with inline buttons for `/proposals open` and `/proposals closed`.
                    *   [ ] If `proposal_id` is present, call `SubmissionService.get_user_submission_for_proposal()`.
                    *   [ ] Send the formatted response string to the user via DM.
            *   [ ] Register the `/my_vote` command handler in `main.py`.
            *   [ ] Write unit tests for the new handler in `user_command_handlers.py`, and new methods in `SubmissionService` and `SubmissionRepository`.

        *   **Subtask 9.5.4: Final Documentation Review & End-to-End Testing**
            *   [ ] Review `intelligentAsks.md`, `projectbrief.md`, `systemPatterns.md`, and `bot_commands.md` to ensure consistency with the implemented features.
            *   [ ] Perform thorough end-to-end manual testing of the enhanced `/ask` flow with various types of natural language queries (testing structured filters, content search, and combined queries).
            *   [ ] Perform thorough end-to-end manual testing of the `/my_vote` command, including the case where no `proposal_id` is provided.

## Phase 10: Comprehensive Testing, Refinement, and Deployment Preparation

**Goal:** Ensure bot stability, reliability, and user-friendliness; prepare for deployment.

**Dependencies:** All previous phases.

**Subtasks:**

1.  **Task 10.1: Unit & Integration Testing (`pytest`)**
    *   [ ] Write unit tests for all core service methods.
    *   [ ] Write unit tests for repository methods (can use in-memory SQLite for some if PostgreSQL is complex to mock, or mock DB session).
    *   [ ] Write unit tests for utility functions.
    *   [ ] Write integration tests for key flows (e.g., proposal creation -> voting -> results).
    *   [ ] Setup `tests/conftest.py` for fixtures (e.g., mock bot, mock db session).

2.  **Task 10.2: Linters and Code Quality Checks**
    *   [ ] Run `pylint` regularly and address issues.
    *   [ ] Ensure consistent code formatting.

3.  **Task 10.3: End-to-End Testing**
    *   [ ] Manually test all commands and user flows as described in `projectbrief.md` testing plan.
    *   [ ] Test with multiple users if possible.
    *   [ ] Test edge cases and error conditions.

4.  **Task 10.4: Logging and Error Handling Refinement**
    *   [ ] Review all logging statements for clarity and usefulness.
    *   [ ] Ensure all user-facing errors are handled gracefully and provide helpful messages.
    *   [ ] Implement more specific custom exceptions where appropriate.

5.  **Task 10.5: Configuration for Production**
    *   [ ] Finalize `.env.example` for production environment variables.
    *   [ ] Prepare deployment scripts/Dockerfile if containerizing.

6.  **Task 10.6: Documentation Review**
    *   [ ] Review `README.md` for setup and usage instructions.
    *   [ ] Ensure all major code components have docstrings.

7.  **Task 10.7: (Future) Admin Access to Voter Info (Post-Closure)**
    *   [ ] Design how admins access this (e.g., a new admin command `/view_proposal_voters <proposal_id>`).
    *   [ ] Implement necessary service and repository methods.
    *   [ ] Ensure clear logging of this access.

This detailed breakdown should provide a solid roadmap for implementation.
