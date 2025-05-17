# Technology Stack and Constraints

See also [systemPatterns.md](./systemPatterns.md) for target architecture and components.

**Telegram Bot Framework:**
    *   **`python-telegram-bot` (PTB):** The most popular and well-documented library. Excellent for handling updates, commands, inline keyboards, etc.

**Database:**
    *   **PostgreSQL (via Supabase):** Supabase will be used as the managed PostgreSQL provider. This offers ease of setup, scalability, and additional features like auth and real-time capabilities (though we'll primarily use its core PostgreSQL functionality).
    *   **SQLAlchemy:** An ORM (Object Relational Mapper) to interact with the Supabase PostgreSQL database in a Pythonic way, using the **`asyncpg`** driver for asynchronous operations.
    *   **Database Migrations:** **Alembic** will be used for managing schema changes against the Supabase database.
        *   **Autogeneration Note:** Autogenerating migration scripts with `alembic revision --autogenerate` can sometimes be unreliable in detecting new tables or changes, even when `env.py` correctly imports models and `target_metadata` is set. Key troubleshooting steps include: 
            *   Ensuring models are imported in `app/persistence/models/__init__.py`.
            *   Explicitly importing model classes (e.g., `from app.persistence.models.user_model import User`) in `alembic/env.py` before `target_metadata = Base.metadata`.
            *   Setting `revision_environment = true` in `alembic.ini` to ensure `env.py` is loaded during the `revision` command. 
            *   If issues persist, manually populating the migration script may be necessary.
    *   **Connection Note:** When connecting to Supabase, prefer using the **Connection Pooler URL** (e.g., `aws-0-<region>.pooler.supabase.com`) provided in the Supabase dashboard. Direct hostnames (e.g., `db.<project_ref>.supabase.co`) may sometimes experience DNS resolution issues, while the pooler endpoint is generally more reliable for application connections.

**Context Engine (RAG - Retrieval Augmented Generation):**
    *   **Vector Database:**
        *   **ChromaDB:** Easy to set up locally, good for development.
    *   **Embedding Model:**
        *   **OpenAI Embeddings API (`text-embedding-3-small`):** 
    *   **LLM for Answering/Summarization:**
        *   **OpenAI API (GPT-4o or similar):** Easiest to integrate for powerful Q&A, summarization of free-form submissions, and for parsing natural language duration inputs for proposal deadlines.

**Scheduling (for deadlines):**
    *   **`APScheduler`:** A good Python library for scheduling tasks (like checking proposal deadlines).

**Core Modules:**
    1.  `bot_main.py`: Initializes bot, sets up handlers, starts polling/webhook.
    2.  `handlers.py`: Contains functions for each command (`/propose`, `/submit`, `/ask`, etc.) and callback queries.
    3.  `db_models.py`: SQLAlchemy models for all tables.
    4.  `db_operations.py`: Functions for CRUD operations on the database.
    5.  `rag_service.py`: Functions for document processing, embedding, vector search, LLM interaction.
    6.  `scheduler_jobs.py`: Functions executed by APScheduler (e.g., `check_proposal_deadlines`), ensuring `asyncio` compatibility when interacting with the bot.
    7.  `config.py`: Non-sensitive configurations. Sensitive data (bot token, channel ID, database URL, API keys) will be managed using environment variables (see Development Practices).

**Development Practices:**
    *   **Configuration Management:** Sensitive data (API tokens, database URL, etc.) will be managed using **environment variables**. For local development, `python-dotenv` will be used to load these from a `.env` file (which will not be committed to Git).
    *   **Dependency Management:** **`requirements.txt`** will be used to list project dependencies.
    *   **Code Quality:** **Pylint** will be used as the primary linter to enforce coding standards and detect errors.
    *   **Testing:** **`pytest`** will be utilized for writing and running unit and integration tests.
    *   **Version Control:** Git will be used for version control.
