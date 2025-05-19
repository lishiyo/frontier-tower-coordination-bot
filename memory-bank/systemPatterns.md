# System Patterns & Architecture: CoordinationBot

This document outlines the system architecture, core components, their responsibilities, interactions, and data flow patterns for the `CoordinationBot`. The design emphasizes modularity, encapsulation, testability, and Python best practices.

## I. Guiding Principles

1.  **Modularity:** Components are designed as distinct modules with well-defined interfaces.
2.  **Encapsulation:** Internal implementation details of a component are hidden from others.
3.  **Single Responsibility Principle (SRP):** Each module or class has a clear and single purpose.
4.  **Dependency Inversion Principle (DIP):** High-level modules do not depend on low-level modules; both depend on abstractions. This is often achieved via Dependency Injection.
5.  **Asynchronous Operations:** All I/O-bound operations (network requests, database interactions) are asynchronous using `async/await`.
6.  **Testability:** Components are designed to be easily testable in isolation, often by mocking their dependencies.
7.  **Scalability:** While starting with PostgreSQL, the separation of concerns allows for future scaling of individual components if needed.

## II. Core Components & Responsibilities

Here's a breakdown of the major components:

1.  **`BotApplication` (Entry Point - `main.py`)**
    *   **Responsibilities:**
        *   Initializes the `python-telegram-bot.Application`.
        *   Loads application configuration (via `ConfigService`).
        *   Sets up all Telegram handlers (command, message, callback query, conversation) by routing them from `telegram_handlers` to the PTB application.
        *   Initializes and provides access to core services (e.g., database session, LLM service).
        *   Starts the `APScheduler` instance (via `SchedulingService`).
        *   Starts the bot (polling or webhook).
    *   **Interactions:** PTB library, `ConfigService`, all handler modules, `SchedulingService`.

2.  **`ConfigService` (`app/config.py`)**
    *   **Responsibilities:**
        *   Loads configuration from environment variables (e.g., API tokens, database URL, channel ID) using `python-dotenv` for local development.
        *   Provides type-safe access to configuration values.
        *   Manages configuration for authorized proposal channels, supporting both single-channel mode (via `TARGET_CHANNEL_ID`) and multi-channel mode (via a list of authorized channel IDs) for the proposal system.
    *   **Interactions:** Used by `BotApplication` and any service needing configuration.

3.  **`TelegramHandlers` (`app/telegram_handlers/`)**
    *   **Modules:** `command_handlers.py`, `callback_handlers.py`, `message_handlers.py` (for conversation steps).
    *   **Responsibilities:**
        *   Define PTB handler functions for specific Telegram updates.
        *   Parse incoming data from Telegram updates (user messages, button clicks, command arguments including optional questions for `/help`).
        *   Manage conversation flows using `ConversationHandler` (e.g., for multi-step proposal creation).
        *   Delegate business logic to appropriate `CoreServices` (`UserService`, `ProposalService`, `SubmissionService`, `ContextService`).
        *   Format responses and send messages back to Telegram (often via `TelegramUtils`).
    *   **Interactions:** PTB library, `CoreServices`, `TelegramUtils`, `LLMService` (for parsing in conversational steps).

4.  **`CoreServices` (`app/core/`)**
    *   Modules: `user_service.py`, `proposal_service.py`, `submission_service.py`, `context_service.py`.
    *   **Responsibilities (General):** Encapsulate the main business logic (use cases) of the application. They are the orchestrators.
        *   `UserService`: Manages user registration (implicit on first interaction), retrieval.
        *   `ProposalService`: Handles proposal creation (including orchestrating conversational context gathering), editing, cancellation, closing (triggered by scheduler), and retrieval. Supports multi-channel functionality where proposals can be posted to different authorized channels, either specified during DM conversation or detected when initiated in-channel.
        *   `SubmissionService`: Handles recording and validation of votes (multiple-choice) and free-form text submissions.
        *   `ContextService`: Manages the RAG pipeline – adding documents/context (from proposers via `/add_doc <proposal_id>` or admins via `/add_global_doc`), editing/deleting these documents, processing queries (`/ask`), interacting with `LLMService` for answer generation/clustering and `VectorDBService` for retrieval. It also handles intelligent help requests by using `LLMService` to interpret user questions against the `bot_commands.md` documentation.
    *   **Interactions:** `Repositories` (for data persistence), other `CoreServices` if necessary, `LLMService`, `VectorDBService`, `TelegramUtils` (for direct notifications if needed).

5.  **`ExternalServices` (`app/services/`)**
    *   Modules: `llm_service.py`, `vector_db_service.py`, `scheduling_service.py`.
    *   **Responsibilities (General):** Abstract interactions with external systems or complex shared functionalities.
        *   `LLMService`: Manages all interactions with the OpenAI API (or other LLM providers). This includes generating embeddings, getting chat completions for Q&A, parsing natural language for proposal durations, clustering free-form submissions, and answering natural language questions based on provided context text (e.g., for the enhanced `/help` command using `bot_commands.md`).
        *   `VectorDBService`: Manages all interactions with the vector database (ChromaDB). Stores, searches, and retrieves text embeddings/chunks.
        *   `SchedulingService`: Configures and runs `APScheduler`. Defines scheduled jobs (e.g., checking for proposal deadlines) that trigger actions in `CoreServices`.
    *   **Interactions:** External APIs (OpenAI), ChromaDB library, `APScheduler` library, `CoreServices`.

6.  **`Persistence Layer` (`app/persistence/`)**
    *   **Modules:**
        *   `database.py`: SQLAlchemy setup (async engine with `asyncpg`), session management (`AsyncSessionLocal`), base for declarative models.
        *   `models/`: Directory containing SQLAlchemy ORM model classes (`User`, `Proposal`, `Submission`, `Document`). Each model in its own file.
            * `Proposal` model includes fields for the proposer, title, description, options, deadline, and crucially, a `target_channel_id` field to specify which channel the proposal should be posted to, enabling multi-channel support.
        *   `repositories/`: Directory containing repository classes that implement the Repository Pattern. Each repository abstracts data access for a specific model (e.g., `UserRepository`, `ProposalRepository`).
    *   **Responsibilities:**
        *   `database.py`: Provide database connection and session utilities.
        *   `models/`: Define the structure of the application's data.
        *   `repositories/`: Encapsulate all database query logic (CRUD operations) for their respective models. `CoreServices` use these repositories to interact with the database, ensuring that business logic is decoupled from data access details.
    *   **Interactions:** SQLAlchemy library, `asyncpg` driver. `CoreServices` interact with `Repositories`.

7.  **`Utilities` (`app/utils/`)**
    *   **Modules:** `telegram_utils.py`, `text_processing.py` (optional, for tasks like text chunking if not handled in `ContextService` or `LLMService`).
    *   **Responsibilities:**
        *   `telegram_utils.py`: Helper functions for common Telegram tasks, like formatting messages with Markdown/HTML, creating inline keyboards, etc.
        *   `text_processing.py`: General text manipulation utilities.
    *   **Interactions:** Used by various components, especially `TelegramHandlers` and `CoreServices`.

## III. Target Directory Structure

```
telegram_bot/
├── main.py                   # Bot entry point, initializes Application
├── app/
│   ├── __init__.py
│   ├── config.py             # Configuration loading (environment variables, non-sensitive defaults)
│   ├── constants.py          # Application-wide constants (e.g., conversation states, callback prefixes)
│   │
│   ├── core/                 # Core business logic, use cases/application services
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── proposal_service.py
│   │   ├── submission_service.py
│   │   └── context_service.py  # Manages RAG pipeline (document ingestion, querying, LLM for RAG tasks)
│   │
│   ├── telegram_handlers/    # Telegram specific handlers & conversation management
│   │   ├── __init__.py
│   │   ├── command_handlers.py # Handlers for commands like /start, /propose, /ask
│   │   ├── callback_handlers.py# Handlers for inline keyboard button presses
│   │   ├── message_handlers.py # Handlers for general messages, conversation steps
│   │   └── conversation_defs.py# Defines ConversationHandler states, entry/fallbacks
│   │
│   ├── services/             # External service integrations & complex shared utilities
│   │   ├── __init__.py
│   │   ├── llm_service.py      # Interacts with OpenAI API (completions, embeddings, duration parsing, clustering)
│   │   ├── vector_db_service.py# Interacts with ChromaDB
│   │   └── scheduling_service.py # APScheduler setup and job definitions
│   │
│   ├── persistence/          # Data persistence layer (database interactions)
│   │   ├── __init__.py
│   │   ├── database.py         # SQLAlchemy setup (async engine with asyncpg), session management
│   │   ├── models/             # SQLAlchemy ORM models (User, Proposal, Submission, Document)
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Base for declarative models
│   │   │   ├── user_model.py
│   │   │   ├── proposal_model.py
│   │   │   ├── submission_model.py
│   │   │   └── document_model.py # Defines Document schema (id, title, hash, url, vector_ids, proposal_id, raw_content)
│   │   ├── repositories/       # Repository pattern for DB access logic
│   │   │   ├── __init__.py
│   │   │   ├── base_repository.py # Optional: Base repository with common CRUD methods
│   │   │   ├── user_repository.py
│   │   │   ├── proposal_repository.py
│   │   │   ├── submission_repository.py
│   │   │   └── document_repository.py
│   │
│   └── utils/                # General utility functions and helper classes
│       ├── __init__.py
│       ├── telegram_utils.py   # Helpers for formatting messages, creating keyboards
│       └── text_processing.py  # Text chunking, cleaning (if not part of other services)
│
├── alembic/                  # Alembic migration scripts and configuration
│   ├── versions/             # Individual migration files
│   ├── env.py                # Alembic environment configuration
│   └── script.py.mako        # Alembic script template
├── tests/                    # Pytest tests
│   ├── __init__.py
│   ├── conftest.py           # Pytest fixtures and global test setup
│   ├── unit/                 # Unit tests for individual components
│   │   ├── core/
│   │   ├── services/
│   │   └── persistence/
│   └── integration/          # Integration tests for component interactions
├── .env.example              # Example environment variables file
├── .gitignore
├── requirements.txt          # Python package dependencies
├── pylintrc                  # Pylint configuration file
├── README.md
```

## IV. Core Data Flows (Examples)

### A. Proposal Creation (with Conversational Context)

1.  **User (Telegram):** Sends `/propose [Initial Information]` (e.g., just `/propose`, or `/propose <Title>`, or `/propose <Title>; <Description>; [Options/"FREEFORM"]`).
2.  **`main.py`/PTB `Application`:** Routes to `CommandHandlers.start_proposal_conversation` (entry point of the `ConversationHandler`).
3.  **`CommandHandlers.start_proposal_conversation`:**
    *   Parses `[Initial Information]` provided by the user.
    *   Stores any successfully parsed details (e.g., title, description, options/type) into `context.user_data`.
    *   Determines the first state of the conversation based on what information is still missing:
        *   If title is missing: Transitions to `COLLECT_TITLE` state. Prompts user for title.
        *   Else if description is missing: Transitions to `COLLECT_DESCRIPTION` state. Prompts user for description.
        *   Else if options/type are missing: Transitions to `COLLECT_OPTIONS_TYPE` state. Prompts user for options or to specify free-form.
        *   Else (all core details provided): Transitions to `ASK_CHANNEL` (if multi-channel mode active and initiated via DM) or directly to `ASK_DURATION`.
4.  **`CommandHandlers.handle_collect_title / handle_collect_description / handle_collect_options_type` (New States):**
    *   User replies with the requested information (title, description, or options/type).
    *   The respective handler saves the input to `context.user_data`.
    *   Transitions to the next collection state (e.g., `COLLECT_TITLE` -> `COLLECT_DESCRIPTION` -> `COLLECT_OPTIONS_TYPE`).
    *   Once all core proposal details (title, description, options/type) are collected, the last handler in this sequence transitions to `ASK_CHANNEL` (if applicable) or `ASK_DURATION`.
5.  **`CommandHandlers.handle_ask_channel` (Optional state, if multi-channel mode active & DM initiated):**
    *   Prompts user to select a target channel from a list of authorized channels.
    *   User selects a channel.
    *   Handler saves `target_channel_id` to `context.user_data`.
    *   Transitions to `ASK_DURATION`.
    *   *Note: If proposal initiated in an authorized channel, `target_channel_id` is set from that channel, and this state is skipped.*
6.  **User (Telegram):** (Assuming in `ASK_DURATION` state) Replies with duration text (e.g., "7 days").
7.  **`CommandHandlers.handle_duration` (`ASK_DURATION` state):**
    *   Calls `LLMService.parse_natural_language_duration(text)` to get `deadline_date`.
    *   Stores `deadline_date` in `context.user_data`.
    *   Transitions to `ASK_CONTEXT` state.
    *   Prompts user for additional context.
8.  **User (Telegram):** Replies with context (text/URL) or "no".
9.  **`CommandHandlers.handle_context` (`ASK_CONTEXT` state):**
    *   If context provided (text/URL):
        *   Calls `ContextService.process_and_store_document(content=user_input, source_type="proposer_initial_chat", title="Initial context for proposal...")`. This involves:
            *   `ContextService` -> `LLMService` (for text embedding if not URL).
            *   `ContextService` -> `VectorDBService` (to store embeddings).
            *   `ContextService` -> `DocumentRepository` (to save document metadata, returning a `document_id`).
        *   Stores `document_id` in `context.user_data`.
    *   Retrieves all proposal data (title, desc, options, type, deadline, proposer_id, context_doc_id, target_channel_id) from `context.user_data`.
    *   Calls `ProposalService.create_new_proposal(proposal_data)`.
10. **`ProposalService.create_new_proposal`:**
    *   Calls `UserRepository.get_or_create(proposer_telegram_id)` to ensure user exists.
    *   Calls `ProposalRepository.add(new_proposal_object)` to save the proposal, getting back the `proposal_id`.
    *   If initial context was added and linked via `document_id` in `proposal_data`, ensures this link is correctly established (e.g., by updating the `Document` entry with the new `proposal_id` if it wasn't known before proposal creation).
11. **`CommandHandlers.handle_context`:**
    *   Receives `proposal_id` from `ProposalService`.
    *   Sends confirmation DM to proposer (e.g., "Proposal #`proposal_id` created... use `/add_doc <proposal_id> ...` for more later").
    *   Calls `TelegramUtils.format_proposal_message(...)` and posts it to the proposal's `target_channel_id` (retrieved from context or proposal object) via PTB's `bot.send_message()`.
    *   Updates the proposal in the DB with `channel_message_id` via `ProposalRepository.update_message_id(proposal_id, channel_msg_id)`.
    *   Ends `ConversationHandler`.

*Notes*: 
- Users can also edit and delete proposals. They can edit a proposal that has not been voted on yet. If the proposal has been voted on already, they have to delete it and make a new proposal.
- Users can view proposals via `/my_proposals`, `/proposals open`, and `/proposals closed`.

### B. User Votes and Submissions

This section covers how users cast votes on multiple-choice proposals, submit free-form responses, and view the results of proposals.

**1. Casting a Vote (Multiple-Choice Proposal):**

1.  **User (Telegram):** Clicks an inline keyboard button on a multiple-choice proposal message in the `target_channel_id`.
2.  **`main.py`/PTB `Application`:** Receives `CallbackQuery` and routes to `CallbackHandlers.handle_vote_callback`.
3.  **`CallbackHandlers.handle_vote_callback`:**
    *   Parses `proposal_id` and `option_index` from `callback_data`.
    *   Retrieves `user_id` from the `update`.
    *   Calls `SubmissionService.record_vote(proposal_id, user_id, option_index)`.
4.  **`SubmissionService.record_vote`:**
    *   Calls `ProposalRepository.get_proposal_by_id(proposal_id)` to verify the proposal is open and of "multiple_choice" type.
    *   Retrieves the actual option string from `proposal.options` using `option_index`.
    *   Calls `UserRepository.register_user_interaction(...)` to ensure the user exists.
    *   Calls `SubmissionRepository.add_or_update_submission(proposal_id, user_id, response_content=selected_option_string)`.
    *   Returns success/failure status.
5.  **`CallbackHandlers.handle_vote_callback`:**
    *   Sends an ephemeral confirmation to the user via `query.answer(...)`.

**2. Submitting a Response (Free-Form Proposal):**

1.  **User (Telegram):** Sends `/submit <proposal_id> <Their text submission>` via DM, often guided by a "Submit Your Idea" button that pre-fills `@BotUsername submit <proposal_id> ` in their DM.
2.  **`main.py`/PTB `Application`:** Routes to `SubmissionCommandHandlers.submit_command` (or `handle_prefilled_submit` which then calls `submit_command`).
3.  **`SubmissionCommandHandlers.submit_command`:**
    *   Parses `proposal_id` and `<text_submission>`.
    *   Retrieves `user_id` from the `update`.
    *   Calls `SubmissionService.record_free_form_submission(proposal_id, user_id, text_submission)`.
4.  **`SubmissionService.record_free_form_submission`:**
    *   Calls `ProposalRepository.get_proposal_by_id(proposal_id)` to verify the proposal is open and of "free_form" type.
    *   Calls `UserRepository.register_user_interaction(...)` to ensure the user exists.
    *   Calls `SubmissionRepository.add_or_update_submission(proposal_id, user_id, response_content=text_submission)`.
    *   Returns success/failure status.
5.  **`SubmissionCommandHandlers.submit_command`:**
    *   Sends a DM confirmation to the user.

**3. Viewing Proposal Results (`/view_results <proposal_id>`):**

1.  **User (Telegram):** Sends `/view_results <proposal_id>` via DM. (If no `proposal_id`, bot prompts on how to find one).
2.  **`main.py`/PTB `Application`:** Routes to `SubmissionCommandHandlers.view_results_command`.
3.  **`SubmissionCommandHandlers.view_results_command`:**
    *   Parses `proposal_id`. If missing, sends guidance and exits.
    *   Calls `ProposalService.get_all_results_for_proposal_view(proposal_id)`.
4.  **`ProposalService.get_all_results_for_proposal_view`:**
    *   Calls `ProposalRepository.get_proposal_by_id(proposal_id)` to fetch the proposal. Ensures it's "closed".
    *   If "multiple_choice": Retrieves vote counts from `proposal.raw_results` (or could re-tally from `SubmissionRepository` if `raw_results` isn't guaranteed to be the sole source of truth for this view).
    *   If "free_form": Retrieves the list of anonymized submissions from `proposal.raw_results`.
    *   Formats the data for display (e.g., vote percentages, list of submissions).
5.  **`SubmissionCommandHandlers.view_results_command`:**
    *   Receives formatted results.
    *   Sends the results to the user via DM, potentially handling message splitting for long lists.

### C. User Asks a Question (`/ask`)

1.  **User (Telegram):** Sends `/ask <question>` or `/ask <proposal_id> <question>`.
2.  **`main.py`/PTB `Application`:** Routes to `CommandHandlers.handle_ask_question`.
3.  **`CommandHandlers.handle_ask_question`:**
    *   Parses `question` and optional `proposal_id`.
    *   Calls `ContextService.get_answer_for_question(question_text, proposal_id_filter)`.
4.  **`ContextService.get_answer_for_question`:**
    *   Calls `LLMService.generate_embedding(question_text)` for the question.
    *   Calls `VectorDBService.search_similar_chunks(question_embedding, proposal_id_filter)` to get relevant document chunks. `proposal_id_filter` helps prioritize proposal-specific context.
    *   Retrieves full text of relevant chunks (possibly from `DocumentRepository` or if `VectorDBService` stores it).
    *   Constructs a prompt for the LLM including retrieved context and the original question.
    *   Calls `LLMService.get_completion(prompt)` to generate an answer.
    *   Formats the answer, including citing sources/snippets.
5.  **`CommandHandlers.handle_ask_question`:**
    *   Receives formatted answer from `ContextService`.
    *   Sends the answer back to the user via DM.

### D. Scheduled Job: Closing Expired Proposals

1.  **`SchedulingService` (`APScheduler`):** Triggers the `check_due_proposals` job periodically.
2.  **`SchedulingService.check_due_proposals_job`:**
    *   Calls `ProposalService.process_expired_proposals()`.
3.  **`ProposalService.process_expired_proposals`:**
    *   Calls `ProposalRepository.find_proposals_past_deadline_and_open()` to get a list of due proposals.
    *   For each due proposal:
        *   Sets proposal status to "closed".
        *   If "multiple_choice":
            *   Calls `SubmissionRepository.get_submissions_for_proposal(proposal_id)`.
            *   Tallies votes. Determines outcome (winner/tie).
            *   Updates `Proposal.outcome` and `Proposal.raw_results` via `ProposalRepository`.
        *   If "free_form":
            *   Calls `SubmissionRepository.get_submissions_for_proposal(proposal_id)`.
            *   Calls `LLMService.cluster_and_summarize_texts([submission.response_content for submission in submissions])`.
            *   Updates `Proposal.outcome` (summary) and `Proposal.raw_results` (full list) via `ProposalRepository`.
        *   Calls `TelegramUtils.format_results_message(...)` and posts results to the proposal's `target_channel_id` (retrieving the channel ID from the proposal record).
        *   (Optional v0/Core v1) Prepares and sends notifications to proposer/voters.

### E. Viewing Document Context

1.  **User (Telegram):** Sends `/view_docs` (or `/view_docs <channel_id>` or `/view_docs <proposal_id>`).
2.  **`main.py`/PTB `Application`:** Routes to a new command handler, e.g., `CommandHandlers.handle_view_documents_router`.
3.  **`CommandHandlers.handle_view_documents_router`:**
    *   Inspects arguments provided.
    *   If no arguments (`/view_docs`): Calls a service (e.g., `ConfigService` or a dedicated `ChannelService`) to get the list of authorized channels. Formats and DMs the list to the user. (Admins can use `/view_global_docs` to list all non-proposal-specific documents).
    *   If `<channel_id>` argument (`/view_docs <channel_id>`): Calls `ProposalService.list_proposals_by_channel(channel_id)`. Formats and DMs the list of proposals to the user, showing their titles (if available, or a snippet/source) and their unique document IDs.
    *   If `<proposal_id>` argument (`/view_docs <proposal_id>`): Calls `ContextService.list_documents_for_proposal(proposal_id)`. Formats and DMs the list of documents to the user, showing their titles (if available, or a snippet/source) and their unique document IDs.
4.  **User (Telegram):** Sends `/view_doc <document_id>`.
    *   Note: This command can be used to view both proposal-specific and global documents.
5.  **`main.py`/PTB `Application`:** Routes to `CommandHandlers.handle_view_document_content`.
6.  **`CommandHandlers.handle_view_document_content`:**
    *   Parses `document_id`.
    *   Calls `ContextService.get_document_content(document_id)`.
7.  **`ContextService.get_document_content`:**
    *   Calls `DocumentRepository.get_document_by_id(document_id)` to fetch the full `Document` object.
    *   Returns the `document.raw_content`.
8.  **`CommandHandlers.handle_view_document_content`:**
    *   Receives the raw text content.
    *   Formats it if necessary (e.g., handling long messages for Telegram) and DMs it to the user.

*Note*: Users can also edit and delete their own documents.

### F. Intelligent Help (`/help <question>`)

1.  **User (Telegram):** Sends `/help how do I see my votes?`.
2.  **`main.py`/PTB `Application`:** Routes to `CommandHandlers.handle_help_command`.
3.  **`CommandHandlers.handle_help_command`:**
    *   Parses the question (e.g., "how do I see my votes?") from the command arguments.
    *   If a question is present, calls `ContextService.get_intelligent_help(question_text)`.
    *   If no question, displays the standard list of commands.
4.  **`ContextService.get_intelligent_help`:**
    *   Loads or accesses the content of `bot_commands.md` (this could be cached or read on demand).
    *   Calls `LLMService.answer_question_from_text(question_text, bot_commands_content)`.
5.  **`LLMService.answer_question_from_text`:**
    *   Constructs a prompt for the LLM, including the user's `question_text` and the `bot_commands_content` as context.
    *   The prompt instructs the LLM to explain how the user can achieve their goal by referencing specific commands and their usage as described in the provided documentation.
    *   Sends the prompt to the LLM and receives the generated explanation.
    *   Returns the formatted explanation.
6.  **`CommandHandlers.handle_help_command`:**
    *   Receives the formatted explanation from `ContextService`.
    *   Sends the explanation back to the user via DM.

### G. User History Commands

This section outlines data flows for commands that allow users to view their own activity and creations.

**1. Viewing Own Votes/Submissions (`/my_votes`):**

1.  **User (Telegram):** Sends `/my_votes` via DM.
2.  **`main.py`/PTB `Application`:** Routes to `UserCommandHandlers.my_votes_command`.
3.  **`UserCommandHandlers.my_votes_command`:**
    *   Retrieves `user_id` from the `update`.
    *   Calls `SubmissionService.get_user_submission_history(user_id)`.
4.  **`SubmissionService.get_user_submission_history`:**
    *   Calls `SubmissionRepository.get_submissions_by_user(user_id)` to get all user's submissions.
    *   For each submission, extracts `proposal_id`.
    *   Collects all unique `proposal_id`s and calls `ProposalRepository.get_proposals_by_ids(list_of_proposal_ids)` to fetch details for all relevant proposals in a batch.
    *   Combines submission data with proposal details (title, status, outcome).
    *   Calls `TelegramUtils.format_datetime_for_display` for timestamps.
    *   Returns a list of formatted history items.
5.  **`UserCommandHandlers.my_votes_command`:**
    *   Receives the formatted history.
    *   Escapes necessary characters for MarkdownV2.
    *   Sends the history to the user via DM, handling message splitting if necessary.

**2. Viewing Own Proposals (`/my_proposals` - Task 7.2):**

1.  **User (Telegram):** Sends `/my_proposals` via DM.
2.  **`main.py`/PTB `Application`:** Routes to `ProposalCommandHandlers.my_proposals_command` (or similar).
3.  **`ProposalCommandHandlers.my_proposals_command`:**
    *   Retrieves `user_id` (proposer_id) from the `update`.
    *   Calls `ProposalService.list_proposals_by_proposer(proposer_id)`.
4.  **`ProposalService.list_proposals_by_proposer`:**
    *   Calls `ProposalRepository.get_proposals_by_proposer_id(proposer_id)`.
    *   Formats the list of proposals (ID, title, status, target_channel_id) for display.
5.  **`ProposalCommandHandlers.my_proposals_command`:**
    *   Receives the formatted list.
    *   Sends the list to the user via DM.

**3. Viewing Own Documents (`/my_docs` - Task 7.6):**

1.  **User (Telegram):** Sends `/my_docs` via DM.
2.  **`main.py`/PTB `Application`:** Routes to `DocumentCommandHandlers.my_docs_command` (or `UserCommandHandlers`).
3.  **`DocumentCommandHandlers.my_docs_command`:**
    *   Retrieves `user_id` from `update`.
    *   Calls `ContextService.list_documents_by_proposer(user_id)`.
4.  **`ContextService.list_documents_by_proposer`:**
    *   Calls `DocumentRepository.get_documents_by_proposer_id(user_id)`.
        *   This repository method will need to join `documents` with `proposals` on `proposal_id` and filter by `proposals.proposer_telegram_id`.
    *   Formats the list of documents (ID, title, associated proposal ID/title) for display.
5.  **`DocumentCommandHandlers.my_docs_command`:**
    *   Receives the formatted list.
    *   Sends the list to the user via DM.

### H. Admin-only Commands

This section describes flows for commands restricted to administrators.

**1. Adding a Global Document (`/add_global_doc`):**

1.  **Admin User (Telegram):** Sends `/add_global_doc <URL or paste text>` or initiates conversation.
2.  **`main.py`/PTB `Application`:** Routes to `AdminCommandHandlers.add_global_doc_command`.
3.  **`AdminCommandHandlers.add_global_doc_command`:**
    *   Verifies user is an admin using `ConfigService`.
    *   Parses URL or text. May enter a conversation to get title/content if not fully provided.
    *   Calls `ContextService.process_and_store_document(content, source_type="admin_global_text/url", title=user_provided_title, proposal_id=None)`.
4.  **`ContextService.process_and_store_document`:** (As described in Proposal Creation, but `proposal_id` is `None`).
    *   Fetches content if URL.
    *   Chunks text.
    *   Generates embeddings via `LLMService`.
    *   Stores document metadata (title, content_hash, source_url, raw_content) in `DocumentRepository`.
    *   Stores embeddings in `VectorDBService`, linking to the SQL `Document.id`.
5.  **`AdminCommandHandlers.add_global_doc_command`:**
    *   Sends confirmation/error DM to admin.

**2. Viewing Global Documents (`/view_global_docs` - Task 7.8):**

1.  **Admin User (Telegram):** Sends `/view_global_docs`.
2.  **`main.py`/PTB `Application`:** Routes to `AdminCommandHandlers.view_global_docs_command`.
3.  **`AdminCommandHandlers.view_global_docs_command`:**
    *   Verifies user is an admin.
    *   Calls `ContextService.list_global_documents()`.
4.  **`ContextService.list_global_documents`:**
    *   Calls `DocumentRepository.get_global_documents()` (e.g., filters for `proposal_id IS NULL`).
    *   Formats list of documents (ID, title).
5.  **`AdminCommandHandlers.view_global_docs_command`:**
    *   Sends formatted list to admin via DM.

**3. Editing a Global Document (`/edit_global_doc <document_id>` - Task 7.8):**

1.  **Admin User (Telegram):** Sends `/edit_global_doc <document_id>` (or `/edit_global_doc` to get prompt).
2.  **`main.py`/PTB `Application`:** Routes to `AdminCommandHandlers.edit_global_doc_command`.
3.  **`AdminCommandHandlers.edit_global_doc_command`:**
    *   Verifies user is an admin.
    *   Parses `document_id`. If missing, sends guidance and exits.
    *   Calls `ContextService.is_global_document(document_id)` to verify.
    *   Initiates conversation or expects follow-up for new content/title.
    *   Calls `ContextService.update_document_content(document_id, new_content, new_title)`.
4.  **`ContextService.update_document_content`:**
    *   Calls `DocumentRepository.update_document(document_id, raw_content=new_content, title=new_title, content_hash=new_hash)`.
    *   Re-chunks `new_content`, generates new embeddings via `LLMService`.
    *   Updates/replaces embeddings in `VectorDBService` associated with `document_id`.
5.  **`AdminCommandHandlers.edit_global_doc_command`:**
    *   Sends confirmation/error DM.

**4. Deleting a Global Document (`/delete_global_doc <document_id>` - Task 7.8):**

1.  **Admin User (Telegram):** Sends `/delete_global_doc <document_id>` (or `/delete_global_doc` to get prompt).
2.  **`main.py`/PTB `Application`:** Routes to `AdminCommandHandlers.delete_global_doc_command`.
3.  **`AdminCommandHandlers.delete_global_doc_command`:**
    *   Verifies user is an admin.
    *   Parses `document_id`. If missing, sends guidance and exits.
    *   Calls `ContextService.is_global_document(document_id)` to verify.
    *   Calls `ContextService.delete_document(document_id)`.
4.  **`ContextService.delete_document`:**
    *   Calls `VectorDBService.delete_embeddings_for_document(document_id)`.
    *   Calls `DocumentRepository.delete_document(document_id)`.
5.  **`AdminCommandHandlers.delete_global_doc_command`:**
    *   Sends confirmation/error DM.

-------

## V. Key Design Patterns & Python Best Practices

*   **Repository Pattern:** Decouples business logic (`CoreServices`) from data access details (`Repositories`). `Repositories` handle all SQLAlchemy query logic.
*   **Service Layer:** `CoreServices` act as a service layer, orchestrating operations and containing business rules.
*   **Dependency Injection (Implicit/Explicit):**
    *   Services and repositories will typically receive their dependencies (e.g., a database session for repositories, other services for core services) upon initialization. This can be managed by a simple DI container or manually during application setup.
*   **Async Everywhere:** Extensive use of `async` and `await` for all I/O-bound operations (Telegram API calls, database, LLM API, vector DB).
*   **Type Hinting:** All functions and methods will have type hints for improved code clarity and to enable static analysis.
*   **Configuration Management:** Centralized configuration via `ConfigService` loading from environment variables.
*   **Error Handling:** Graceful error handling with informative feedback to users and logging for developers. Custom exceptions can be defined for specific error conditions.
*   **Logging:** Comprehensive logging throughout the application using Python's `logging` module.
*   **PTB `ConversationHandler`:** Used for managing multi-step interactions like proposal creation.
*   **Alembic for Migrations:** Database schema changes managed through Alembic.

This architecture aims to provide a solid foundation for `CoordinationBot`, allowing for easier development, testing, and future expansion.