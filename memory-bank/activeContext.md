# Active Context - Sat May 17 18:21:49 PDT 2025

## Current Work Focus
- **Phase 5 Started:** Tasks 5.1 (Scheduler Setup) and 5.2 (Deadline Checking Job) largely completed.
- Next is Task 5.3 (LLM Clustering for Free-Form Proposals).
- Requires thorough manual testing of the newly implemented scheduler and deadline processing logic.

## What's Working
- **Scheduler:** `APScheduler` is integrated into the bot's lifecycle (`main.py`).
- **Deadline Job:** `check_proposal_deadlines_job` is defined in `SchedulingService` and scheduled to run (currently every 1 minute for testing).
- **Expired Proposal Processing (`ProposalService.process_expired_proposals`):
    - Correctly fetches expired open proposals.
    - Calculates outcomes for multiple-choice proposals by tallying votes.
    - Stores a placeholder summary for free-form proposals (actual LLM clustering is Task 5.3).
    - Updates proposal status to "CLOSED" and populates `outcome` and `raw_results` fields in the database.
    - Posts a formatted results message to the proposal's target channel, replying to the original proposal message.
- **Service Dependencies:** `ProposalService` constructor now accepts `bot_app` (Telegram `Application` instance), allowing it to send messages. This is passed correctly from `SchedulingService`.
- Previous features (proposal creation, voting, `/submit` command, prefilled submit handling via `@botname submit...`) are stable.

## What's Broken or Pending
- **LLM Clustering (Task 5.3):** The actual LLM-based summarization for free-form proposals is not yet implemented in `LLMService`; `ProposalService` uses a placeholder.
- The `PTBUserWarning` regarding `per_message=False` in `ConversationHandler` persists (known and accepted).

## Active Decisions and Considerations
- The scheduler interval for `check_proposal_deadlines_job` is 1 minute for easier testing. This will need to be increased for a production environment (e.g., 5-15 minutes).
- The results message posted by `ProposalService` is currently formatted directly within the service. A dedicated helper in `telegram_utils.py` could be added later if more complex formatting is needed.

## Learnings and Project Insights
- For services (like `ProposalService`) that need to perform actions outside typical Telegram handler flows (e.g., sending messages from a scheduled job), they must be provided with the Telegram `Application` or `Bot` instance.
- Scheduled jobs requiring database access should manage their own `AsyncSessionLocal` to ensure proper session scoping and lifecycle.
- Careful consideration of timezones is important for deadline calculations. Using `UTC` for the scheduler and `func.now()` (which is timezone-aware in PostgreSQL) for database comparisons is a robust approach.

## Current Database/Model State
- No database schema changes were introduced in Tasks 5.1 or 5.2.
- The `proposals` table will now be actively managed by the scheduler: `status` will change to `CLOSED`, and `outcome` and `raw_results` will be populated for expired proposals.

## Next Steps
- Manually test the deadline processing and results posting functionality (details to be added to `testing_instructions.md`).
- Implement Task 5.3: `LLMService.cluster_and_summarize_texts`.
- Update `progress.md` with today's advancements.
