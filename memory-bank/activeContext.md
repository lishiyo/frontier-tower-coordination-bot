# Active Context - Fri May 16 21:05:44 PDT 2025

## Current Work Focus
- Completed Task 2.1: User Model & Repository.
- Moving to Phase 2, Task 2.2: Implicit User Registration.

## What's Working
- Task 2.1 is fully complete.
    - `User` SQLAlchemy model is defined.
    - `UserRepository` with `get_or_create_user` and `get_user_by_telegram_id` is implemented.
    - The `users` table has been successfully migrated to the Supabase PostgreSQL database using Alembic.
- Database connectivity established using the Supabase connection pooler URL.
- Core project structure, basic bot commands (`/start`, `/help`), and Alembic setup are functional from Phase 1.

## What's Broken
- No known issues related to the completed Task 2.1.

## Active Decisions and Considerations
- Confirmed that using the Supabase connection pooler URL is more reliable for database connections than the direct database hostname, which exhibited DNS resolution issues.

## Learnings and Project Insights
- Direct Supabase database hostnames (e.g., `db.<project_ref>.supabase.co`) can sometimes have DNS resolution problems. Connection pooler hostnames (e.g., `aws-0-<region>.pooler.supabase.com`) are a more robust alternative for application connectivity.
- Always verify hostname resolution (e.g., using `dig @8.8.8.8 <hostname>`) as a first step when troubleshooting database connection errors like `socket.gaierror`.
- Ensuring `app/config.py` correctly constructs the database URL from individual components is vital if not using a single `DATABASE_URL` environment variable.
- Explicitly importing models in `alembic/env.py` can improve the reliability of Alembic's autogenerate feature.

## Current Database/Model State
- The `users` table now exists in the Supabase PostgreSQL database.
- Schema for `users` table:
    - `id` (Integer, Primary Key, Auto-increment)
    - `telegram_id` (Integer, Unique, Index, Not Null)
    - `username` (String, Nullable)
    - `first_name` (String, Nullable)
    - `last_updated` (DateTime with timezone, Not Null, server_default='now()')

## Next Steps
- Task 2.2: Implement implicit user registration logic that utilizes the `UserService` and `UserRepository`.
