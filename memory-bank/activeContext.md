# Active Context - Fri May 16 21:25:44 PDT 2025

## Current Work Focus
- Completed Task 2.2: Implicit User Registration.
- Completed Task 2.3: Proposal Model & Repository.
- Moving to Phase 2, Task 2.4: Basic `/propose` Command (Static Duration for now).

## What's Working
- Implicit user registration via `UserService` in `start_command`.
- `Proposal` model and `ProposalRepository` are defined.
- The `proposals` table has been created in the database via a manually populated Alembic migration (`0cb97eaf1e36_create_proposal_table.py`).
- Alembic configuration (`alembic.ini`, `env.py`, `models/__init__.py`) updated to best practices for autogeneration, though it required manual intervention for the `proposals` table.

## What's Broken
- Alembic autogeneration for new tables was unreliable for the `proposals` table, requiring manual creation of the migration script despite `target_metadata` appearing correct in debug logs. This might need monitoring for future model changes.

## Active Decisions and Considerations
- Proceeding with manually assisted Alembic migrations if autogeneration continues to be problematic, to avoid getting blocked.
- The `ProposalRepository` includes several methods (`find_expired_open_proposals`, `update_proposal_status`, etc.) that were listed in later tasks but were convenient to add now as they relate directly to the `Proposal` model.

## Learnings and Project Insights
- Setting `revision_environment = true` in `alembic.ini` is crucial for `env.py` to be loaded during `alembic revision` and for `target_metadata` to be correctly populated for autogeneration.
- Ensuring `app/persistence/models/__init__.py` imports all model classes can also aid discovery.
- Even with these settings, Alembic autogeneration might not always detect all changes perfectly, and manual script creation/adjustment can be a necessary fallback.

## Current Database/Model State
- The `users` table exists.
- The `proposals` table now exists in the Supabase PostgreSQL database.
- Schema for `proposals` table:
    - `id` (Integer, PK, Auto-increment, Index)
    - `proposer_telegram_id` (Integer, FK to `users.telegram_id`, Not Null, Index)
    - `title` (String, Not Null)
    - `description` (Text, Not Null)
    - `proposal_type` (String, Not Null) (e.g., "multiple_choice", "free_form")
    - `options` (JSON, Nullable)
    - `channel_message_id` (Integer, Nullable)
    - `creation_date` (DateTime with timezone, Not Null, server_default='now()')
    - `deadline_date` (DateTime with timezone, Not Null)
    - `status` (String, Not Null, server_default='open') (e.g., "open", "closed", "cancelled")
    - `outcome` (Text, Nullable)
    - `raw_results` (JSON, Nullable)

## Next Steps
- Task 2.4: Basic `/propose` Command (Static Duration for now).
