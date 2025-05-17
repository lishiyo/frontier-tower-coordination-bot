# Progress Log

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
