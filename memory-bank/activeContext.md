# Active Context - Wed May 14 16:29:25 PDT 2025

## Current Work Focus
- Completed Phase 1: Project Foundation & Basic Bot Setup.
- Moving to Phase 2: User Management and Core Proposal Features (Static), starting with Task 2.1: User Model & Repository.

## What's Working
- Basic bot structure is in place (`main.py`, `app/config.py`).
- `/start` and `/help` commands are functional.
    - Welcome and help messages are displayed.
    - HTML formatting for help message is working correctly.
- Bot starts and runs without asyncio event loop errors.
- Initial unit tests for command handlers are created.
- Manual testing instructions are documented.

## What's Next
- Task 2.1: User Model & Repository
    - Define `User` SQLAlchemy model in `app/persistence/models/user_model.py`.
    - Create `app/persistence/repositories/user_repository.py` with `get_or_create_user`.
    - Generate and apply Alembic migration for the `User` table.

## Project Decisions
- Using Supabase PostgreSQL as the managed database solution.
- Using SQLAlchemy with `asyncpg` for asynchronous database operations.
- Using Alembic for database migrations.
- Using `python-telegram-bot` as the Telegram bot framework.
- Using HTML (`ParseMode.HTML`) for Telegram message formatting due to better handling of special characters compared to Markdown.

## Learnings and Project Insights
- `python-telegram-bot`'s `application.run_polling()` manages its own event loop; `asyncio.run()` should not wrap the main function if `run_polling()` is used directly.
- Telegram's Markdown parsing is strict. HTML parsing (`ParseMode.HTML`) is generally more robust for messages with complex formatting or special characters.
- `pytest-asyncio` is required for testing `async def` test functions with `pytest`.
- Commenting out unused imports (like `DatabaseManager` before implementation) prevents `ImportError`.

## Current Database/Model State
- Supabase project created and connection details are in `.env`.
- Alembic is configured.
- `app/persistence/database.py` sets up SQLAlchemy Base.
- No application-specific database tables (e.g., for Users, Proposals) have been defined or migrated yet. Phase 2 will address this.
