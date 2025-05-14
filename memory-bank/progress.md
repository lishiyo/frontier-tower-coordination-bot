# Progress Log

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
