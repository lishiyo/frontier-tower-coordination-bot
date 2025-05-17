# Active Context - Fri May 16 22:41:10 PDT 2025

## Current Work Focus
- Completed Task 2.4: Basic `/propose` command.
- Preparing for Task 2.5: Database migration to add `target_channel_id` to the `Proposal` model.

## What's Working
- Basic `/propose` command functionality (DM-only initiation, static duration, posts to single `TARGET_CHANNEL_ID`).
- User registration (`/start` command).
- Error handling for `switch_inline_query_current_chat` button in channel messages (button removed, relying on text instructions).
- Design documents (`projectbrief.md`, `systemPatterns.md`, `tasks.md`) have been updated to incorporate future multi-channel proposal capabilities and current schema adjustments.

## What's Broken
- The `proposals` table schema is missing the `target_channel_id` field, which is planned for multi-channel support. This will be addressed in Task 2.5.

## Active Decisions and Considerations
- Decided to implement `target_channel_id` in the schema now (Task 2.5) to prepare for future multi-channel support, while the current `/propose` implementation (Task 2.4) uses the single `TARGET_CHANNEL_ID` from config.
- Removed the interactive "Submit Your Idea" button from channel messages for free-form proposals due to Telegram API limitations, opting for clear text-based instructions instead.

## Learnings and Project Insights
- `switch_inline_query_current_chat` buttons are unreliable when used in bot messages posted to channels. Direct text instructions are a more robust alternative for guiding users to DM the bot.
- It's important to align task planning (`tasks.md`) with model evolution. We identified the need for a new migration task (2.5) after realizing the `target_channel_id` was introduced in design docs but not yet in the implemented `Proposal` model from Task 2.3.

## Current Database/Model State
- The `users` table exists.
- The `proposals` table exists but is missing the `target_channel_id` column. This column will be added in Task 2.5.
- Schema for `proposals` table (target state after Task 2.5):
    - `id` (Integer, PK, Auto-increment, Index)
    - `proposer_telegram_id` (Integer, FK to `users.telegram_id`, Not Null, Index)
    - `title` (String, Not Null)
    - `description` (Text, Not Null)
    - `proposal_type` (String, Not Null)
    - `options` (JSON, Nullable)
    - `target_channel_id` (String or Integer, Not Null) - NEW, will store the ID of the channel where the proposal is posted.
    - `channel_message_id` (Integer, Nullable)
    - `creation_date` (DateTime with timezone, Not Null, server_default='now()')
    - `deadline_date` (DateTime with timezone, Not Null)
    - `status` (String, Not Null, server_default='open')
    - `outcome` (Text, Nullable)
    - `raw_results` (JSON, Nullable)

## Next Steps
- Task 2.5: Add Multi-Channel Support to Proposal Model (Database Migration & Code Updates).
    - Update `app/persistence/models/proposal_model.py`.
    - Generate and apply Alembic migration.
    - Update relevant repository and service methods.
