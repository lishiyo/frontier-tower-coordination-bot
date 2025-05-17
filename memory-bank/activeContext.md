# Active Context - Fri May 16 22:51:12 PDT 2025

## Current Work Focus
- Completed Task 2.5: Add Multi-Channel Support to Proposal Model (database migration, model, repository, service, and command handler updates).
- `/propose` command is functional with the new `target_channel_id` field (still in single-channel mode).
- Preparing to start Phase 3: Conversational Proposal Creation & Initial Context.

## What's Working
- Task 2.5 implementation is complete and tested by the user for the `/propose` command flow.
- The `proposals` table now includes `target_channel_id`.
- Alembic migration for `target_channel_id` handles backfilling existing rows (if `TARGET_CHANNEL_ID` env var is set during migration) and sets the column to non-nullable.
- Core services and repositories related to proposal creation are updated for `target_channel_id`.
- `command_handlers.py` correctly passes `target_channel_id` for new proposals.

## What's Broken
- No known issues related to the completed Task 2.5.

## Active Decisions and Considerations
- The system currently operates in a single-channel mode, using the `TARGET_CHANNEL_ID` from `ConfigService` as the `target_channel_id` for all proposals. Full multi-channel selection logic is deferred to a later task (Task 8.8).

## Learnings and Project Insights
- Ensuring all layers of the application (handler, service, repository, model, migration) are updated consistently for schema changes is crucial to avoid runtime errors like `TypeError`.
- Accessing environment variables within Alembic migration scripts for data backfills (like for `TARGET_CHANNEL_ID`) should be handled with awareness that the variable must be present in the migration execution environment.

## Current Database/Model State
- The `users` table exists.
- The `proposals` table now includes the `target_channel_id` (String, Not Null) column.
- Schema for `proposals` table:
    - `id` (Integer, PK, Auto-increment, Index)
    - `proposer_telegram_id` (Integer, FK to `users.telegram_id`, Not Null, Index)
    - `title` (String, Not Null)
    - `description` (Text, Not Null)
    - `proposal_type` (String, Not Null)
    - `options` (JSON, Nullable)
    - `target_channel_id` (String, Not Null)
    - `channel_message_id` (Integer, Nullable)
    - `creation_date` (DateTime with timezone, Not Null, server_default='now()')
    - `deadline_date` (DateTime with timezone, Not Null)
    - `status` (String, Not Null, server_default='open')
    - `outcome` (Text, Nullable)
    - `raw_results` (JSON, Nullable)

## Next Steps
- Begin Phase 3: Conversational Proposal Creation & Initial Context.
    - Task 3.1: LLM Service Setup: Create `app/services/llm_service.py` and implement initial functions.
