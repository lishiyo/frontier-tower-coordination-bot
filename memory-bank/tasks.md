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
                *   [ ] Call `LLMService.cluster_and_summarize_texts([sub.response_content for sub in submissions])` (needs implementation in `LLMService`). (Placeholder implemented)
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
    *   [ ] In `app/telegram_handlers/document_command_handlers.py` (or appropriate admin command handler file), implement `add_global_doc_command` handler.
        *   [ ] Check if user is an admin (loaded from `ConfigService`).
        *   [ ] Parse URL or pasted text.
        *   [ ] Prompt for a document title if not easily inferable.
    *   [ ] `add_global_doc_command` calls `ContextService.process_and_store_document(content, source_type="admin_global_upload", title=user_provided_title, proposal_id=None)`.
    *   [ ] Send confirmation to admin.

2.  **Task 6.2: Implement `/ask` Command**
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

3.  **Task 6.3: Enhance URL Content Extraction**
    *   [ ] Research and select a robust HTML parsing/content extraction library or method (e.g., BeautifulSoup, trafilatura, crawl4ai, Firecrawl tools). crawl4ai preferred.
    *   [ ] Implement the chosen solution within `ContextService._fetch_content_from_url` to replace the basic `response.text`.
    *   [ ] Ensure the new implementation extracts clean, main content from web pages, stripping HTML tags, scripts, and other noise.
    *   [ ] Test with various URLs to confirm improved context quality for RAG.

## Phase 7: User History, Proposal Management Commands & Privacy

**Goal:** Add commands for user history, proposal viewing/management, and privacy policy.

**Dependencies:** Phase 2 (Proposals), Phase 4 (Submissions), Phase 3 (ContextService for `/add_doc`)

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

5.  **Task 7.5: Implement `/add_doc` Command (Proposer Only)**
    *   [ ] In `ProposalRepository`, ensure `get_proposal_by_id` fetches `proposer_id`.
    *   [ ] Implement `add_doc_command` in `command_handlers.py`:
        *   [ ] Parse `proposal_id`.
        *   [ ] Verify user is the proposer of `proposal_id`.
        *   [ ] If text/URL provided in command, call `ContextService.process_and_store_document(content, proposal_id=proposal_id, source_type="proposer_added_context")`.
        *   [ ] (Optional) Could initiate a short conversation if no context provided in command.
    *   [ ] Send confirmation/error DM.

6.  **Task 7.6: Implement `/view_results` Command**
    *   [ ] In `ProposalService`, implement `get_all_results_for_proposal_view(proposal_id)`:
        *   [ ] Fetch proposal. Ensure it's "closed".
        *   [ ] Free "multiple_choice" results, fetch the total vote counts for each of the options.
        *   [ ] For "free_form" results, fetch `proposal.raw_results` (which should contain the list of anonymized submissions).
        *   [ ] Format for display.
    *   [ ] Implement `view_results_command` in `submission_command_handlers.py`.

7.  **Task 7.7: Implement `/privacy` Command**
    *   [ ] Create a static privacy policy text.
    *   [ ] Implement `privacy_command` in `command_handlers.py` to send this text.

8.  **Task 7.8: Implement Proposer Document Editing and Deletion**
    *   **Implement `/edit_doc <document_id>` Command (Proposer Only):**
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
    *   **Implement `/delete_doc <document_id>` Command (Proposer Only):**
        *   [ ] In `app/telegram_handlers/document_command_handlers.py` (or similar), implement `delete_doc_command`.
        *   [ ] Handler parses `document_id`.
        *   [ ] Use `ContextService.can_user_edit_document()` (or a similar `can_user_delete_document`) to verify proposer.
        *   [ ] In `ContextService`, add `delete_document(document_id)`:
            *   [ ] Removes associated embeddings from `VectorDBService`.
            *   [ ] Deletes document from `DocumentRepository`.
        *   [ ] Call `ContextService.delete_document()`.
        *   [ ] Send confirmation/error DM.

9.  **Task 7.9: Implement Admin Global Document Management (List, Edit, Delete)**
    *   **Implement `/view_global_docs` Command (Admin Only):**
        *   [ ] In `app/telegram_handlers/document_command_handlers.py` (or admin handlers), implement `view_global_docs_command`.
        *   [ ] Verify user is an admin.
        *   [ ] In `DocumentRepository`, add `get_global_documents()` (e.g., where `proposal_id` is NULL).
        *   [ ] In `ContextService`, add `list_global_documents()` that calls the repository method and formats a list (ID, title).
        *   [ ] DM the list to the admin.
    *   **Implement `/edit_global_doc <document_id>` Command (Admin Only):**
        *   [ ] In `app/telegram_handlers/document_command_handlers.py` (or admin handlers), implement `edit_global_doc_command`.
        *   [ ] Verify user is an admin.
        *   [ ] Handler parses `document_id`.
        *   [ ] In `ContextService`, add `is_global_document(document_id)` (checks if `proposal_id` is NULL).
        *   [ ] Verify document is a global document using `ContextService.is_global_document()`.
        *   [ ] Initiate a conversation (or expect further message) for new content/title.
        *   [ ] Call `ContextService.update_document_content()` (from Task 7.8).
        *   [ ] Send confirmation/error DM.
    *   **Implement `/delete_global_doc <document_id>` Command (Admin Only):**
        *   [ ] In `app/telegram_handlers/document_command_handlers.py` (or admin handlers), implement `delete_global_doc_command`.
        *   [ ] Verify user is an admin.
        *   [ ] Handler parses `document_id`.
        *   [ ] Verify document is a global document using `ContextService.is_global_document()`.
        *   [ ] Call `ContextService.delete_document()` (from Task 7.8).
        *   [ ] Send confirmation/error DM.

## Phase 8: Multi-Channel Support Enhancements

**Goal:** Extend multi-channel capabilities to proposal creation, listing, and context document viewing.

**Dependencies:** Initial multi-channel setup (from previous Phase 8 tasks if they exist, or core single-channel features). Core document viewing from Task 3.5.

**Subtasks:**

1.  **Task 8.1: Multi-Channel Proposal System Implementation (Core)**
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

2.  **Task 8.2: Enhance `/view_docs` for Multi-Channel Support**
    *   [ ] **`/view_docs` (no arguments):**
        *   [ ] Modify handler to retrieve the list of *all* authorized channels from `ConfigService` (or `AuthorizedChannelRepository`).
        *   [ ] Format and DM this list (channel IDs and names if available) to the user.
    *   [ ] **`/view_docs <channel_id>`:**
        *   [ ] Ensure this command correctly lists proposals for *any* valid authorized `channel_id` (not just the old single `TARGET_CHANNEL_ID`). No significant change if `ProposalService.list_proposals_by_channel` already just takes a `channel_id`.
    *   [ ] **General Document Association (Future Consideration for RAG):**
        *   [ ] Consider if general documents (added via `/add_global_doc`) should be associable with specific authorized channels (new `associated_channel_id` field in `Document` model).
        *   [ ] If so, `/view_docs <channel_id>` could also list general documents associated with that channel.
        *   [ ] RAG queries via `/ask` could then also be filtered/prioritized by documents relevant to the channel a user is in or asking about.

3.  **Task 8.3: Testing Multi-Channel Document Viewing**
    *   [ ] Configure multiple authorized channels.
    *   [ ] Test `/view_docs` (no args) lists all configured channels.
    *   [ ] Test `/view_docs <channel_id>` for different authorized channels, ensuring correct proposal listings.
    *   [ ] Ensure `/view_docs <proposal_id>` and `/view_doc <document_id>` continue to function correctly regardless of how many channels are configured.

4.  **Task 8.4: Implement Intelligent Help via LLM (`/help <question>`)**
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
        *   [ ] Implement `answer_question_from_docs(question, docs_content)` in `app/services/llm_service.py`:
            *   [ ] Construct a prompt for the LLM that includes the `docs_content` and the user's `question`.
            *   [ ] The prompt should instruct the LLM to use the provided `docs_content` to answer the `question` by explaining relevant commands and their usage.
            *   [ ] Call the LLM completion endpoint and return the answer.
        *   [ ] Ensure the `help_command` handler sends the response from the service back to the user via DM.
        *   [ ] Test with various questions to ensure clarity and accuracy of LLM responses.

## Phase 9: Comprehensive Testing, Refinement, and Deployment Preparation

**Goal:** Ensure bot stability, reliability, and user-friendliness; prepare for deployment.

**Dependencies:** All previous phases.

**Subtasks:**

1.  **Task 9.1: Unit & Integration Testing (`pytest`)**
    *   [ ] Write unit tests for all core service methods.
    *   [ ] Write unit tests for repository methods (can use in-memory SQLite for some if PostgreSQL is complex to mock, or mock DB session).
    *   [ ] Write unit tests for utility functions.
    *   [ ] Write integration tests for key flows (e.g., proposal creation -> voting -> results).
    *   [ ] Setup `tests/conftest.py` for fixtures (e.g., mock bot, mock db session).

2.  **Task 9.2: Linters and Code Quality Checks**
    *   [ ] Run `pylint` regularly and address issues.
    *   [ ] Ensure consistent code formatting.

3.  **Task 9.3: End-to-End Testing**
    *   [ ] Manually test all commands and user flows as described in `projectbrief.md` testing plan.
    *   [ ] Test with multiple users if possible.
    *   [ ] Test edge cases and error conditions.

4.  **Task 9.4: Logging and Error Handling Refinement**
    *   [ ] Review all logging statements for clarity and usefulness.
    *   [ ] Ensure all user-facing errors are handled gracefully and provide helpful messages.
    *   [ ] Implement more specific custom exceptions where appropriate.

5.  **Task 9.5: Configuration for Production**
    *   [ ] Finalize `.env.example` for production environment variables.
    *   [ ] Prepare deployment scripts/Dockerfile if containerizing.

6.  **Task 9.6: Documentation Review**
    *   [ ] Review `README.md` for setup and usage instructions.
    *   [ ] Ensure all major code components have docstrings.

7.  **Task 9.7: (Future) Admin Access to Voter Info (Post-Closure)**
    *   [ ] Design how admins access this (e.g., a new admin command `/view_proposal_voters <proposal_id>`).
    *   [ ] Implement necessary service and repository methods.
    *   [ ] Ensure clear logging of this access.

This detailed breakdown should provide a solid roadmap for implementation.
