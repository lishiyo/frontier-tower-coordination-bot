# Implementation Milestones and Testing Plan

Here's a structured approach to testing our `CoordinationBot`:

**I. Test Environment Setup**

1.  **Separate Test Bot:**
    *   Go to BotFather on Telegram.
    *   Create a *new* bot specifically for testing (e.g., `FrontierTowerTestBot`). Get its API token.
    *   **Crucially, use this test token in your development environment.** Do not use your production bot token for testing.

2.  **Test Channel:**
    *   Create a new private Telegram channel (e.g., "FT Bot Test Channel").
    *   Add your `FrontierTowerTestBot` to this channel as an administrator. Make sure it has permissions to post messages.
    *   Get the Channel ID. You can do this by:
        *   Forwarding a message from the channel to a bot like `@JsonDumpBot` or `@userinfobot`. The `chat.id` in the forwarded message's JSON will be your channel ID (it's usually a negative number).
        *   Temporarily making the channel public, using its `@username` and then converting it to ID using another bot, then making it private again.

3.  **Test Users:**
    *   You will be one test user.
    *   Ideally, get 1-2 colleagues or friends to act as other test users. This helps test multi-user interactions and ensures things look right from different perspectives. They will need to DM your `FrontierTowerTestBot`.

4.  **Test Database:**
    *   Ensure your bot script connects to a separate database for testing (e.g., a different Supabase project or a local PostgreSQL instance if preferred for isolated testing, though Supabase staging environments are also an option). You don't want to pollute your production database with test data.
    *   Have an easy way to wipe and reset this test database.

5.  **Local RAG Setup:**
    *   Use a local vector database (like ChromaDB running in-memory or with local persistence) for testing the `/ask` functionality.
    *   Prepare a few sample documents to load for context.

**II. Testing Phases & What to Test**

**Phase 1: Basic Bot Interaction & Setup**

*   **`/start` command:**
    *   DM your test bot `/start`.
    *   Verify: You receive the welcome message. Your user info is (implicitly) added to the test database.
*   **Help command (`/help`):**
    *   Verify: You receive a list of available commands.
*   **Invalid commands:**
    *   Send a random command like `/fooobar`.
    *   Verify: The bot responds gracefully (e.g., "Unknown command. Try /help.").

**Phase 2: Proposal Creation Workflow**

*   **Valid Proposal:**
    *   DM test bot: `/propose Test Event; Let's decide on a test event; Workshop, Social Gathering, Demo Day; 1` (short duration for quick testing).
    *   Verify (Proposer's DM): You receive a confirmation message.
    *   Verify (Database): A new proposal entry exists with correct title, description, options, proposer ID, status "open", and calculated deadline.
    *   Verify (Test Channel):
        *   A new message is posted by the bot.
        *   The message format is correct (title, proposer, description, options, deadline).
        *   An inline keyboard with the voting options ("Workshop", "Social Gathering", "Demo Day") is present.
*   **Invalid Proposal Formats:**
    *   `/propose Missing parts; Description only`
    *   `/propose Title; Desc; Opt1,Opt2; NotANumberForDays`
    *   `/propose Title; Desc; OnlyOneOption; 1`
    *   Verify: The bot DMs you an error message explaining the issue. No proposal is created in the DB or posted to the channel.

**Phase 3: Voting Workflow**

*   **First Vote:**
    *   In the test channel, as Test User 1, click the "Workshop" button on the proposal message.
    *   Verify (Voter's side): You receive a "vote recorded" ephemeral message (or a DM if you design it that way). The inline keyboard might disappear or update.
    *   Verify (Database): A new vote entry exists linking your `telegram_id` to the proposal ID and "Workshop".
    *   Verify (Anonymity): No public message in the channel indicates *who* voted or *what* they voted for.
*   **Second Vote (Different User):**
    *   As Test User 2 (or yourself using a different Telegram account if possible, or just simulate by changing `user_id` in your test script if you're only one person), click "Social Gathering".
    *   Verify (Database): Another vote entry for the same proposal, different user, different option.
*   **Changing a Vote:**
    *   As Test User 1, click "Social Gathering" on the same proposal.
    *   Verify (Database): The existing vote for Test User 1 for that proposal is updated to "Social Gathering" (or you have logic to prevent/allow changes and test that).
*   **Voting on a Closed Proposal (Test later after deadline passes):**
    *   Attempt to vote.
    *   Verify: Vote is rejected, user is notified.

**Phase 4: Deadline Management & Results Announcement**

*   **Let Deadline Pass:**
    *   Wait for the short (e.g., 1 day, or even 5 minutes for quick testing, by setting a deadline in the near past) deadline of your test proposal to pass.
    *   Ensure your scheduler (`APScheduler` or `JobQueue`) is running.
*   **Verify (Database):**
    *   The proposal's `status` is changed to "closed".
    *   The `outcome` field is populated correctly based on the votes (e.g., "Social Gathering wins with 2 votes").
*   **Verify (Test Channel):**
    *   The bot posts a results message.
    *   The results message should clearly state the outcome and the vote counts/percentages for each option.
    *   It might edit the original proposal message or reply to it.

**Phase 5: Information Retrieval (RAG)**

*   **Add Documents:**
    *   Use an admin command (`/add_global_doc <URL or text>`) to feed 2-3 sample policy documents into the bot's context.
    *   Verify (Database/VectorDB): Documents are processed and stored/indexed.
*   **Ask Questions:**
    *   DM test bot: `/ask What is our policy on snacks?` (assuming "snacks" is in one of your test docs).
    *   Verify: Bot responds with relevant information from the document.
    *   DM test bot: `/ask What is the meaning of life?` (assuming this is NOT in your docs).
    *   Verify: Bot responds with "I don't have enough information..." or similar.
    *   DM test bot: `/ask Tell me about the event policy.`
    *   Verify: Bot provides a summary or relevant snippets.

**Phase 6: User Data & History**

*   **`/myvotes`:**
    *   DM the bot this command.
    *   Verify: It lists the proposals you (Test User 1) voted on and what your vote was.
*   **`/proposals open`:**
    *   Verify: It lists any proposals still open for voting.
*   **`/proposals closed`:**
    *   Verify: It lists the "Test Event" proposal with its outcome.

**III. Automated Testing (Python `unittest` or `pytest`)**

While manual end-to-end testing is vital for Telegram bots, you should also write unit tests for your core logic that *doesn't* directly involve the Telegram API.

*   **Command Parsing:** Test the functions that parse arguments from commands like `/propose`.
*   **Date Calculations:** Test deadline calculation logic.
*   **Vote Tallying:** Test the function that takes a list of votes and determines the winner.
*   **RAG Logic (without LLM calls):** If you have functions that prepare prompts or process LLM output, test those.
*   **Database Interactions:** You can test your SQLAlchemy models and basic CRUD operations (though this can sometimes bleed into integration testing). Mock the database session for pure unit tests.

**Example `pytest` structure (conceptual):**

```python
# tests/test_proposal_logic.py
from your_bot_module.db_models import Proposal
from your_bot_module.commands import parse_propose_command # Fictional function

def test_parse_propose_valid():
    args = "Event Title; Event Description; Option A,Option B; 7".split(";")
    parsed = parse_propose_command_parts(args) # Your parsing logic
    assert parsed['title'] == "Event Title"
    assert parsed['duration_days'] == 7
    assert len(parsed['options']) == 2

def test_tally_votes():
    from your_bot_module.scheduler_jobs import _tally_proposal_votes # Fictional
    mock_votes = [
        {'selected_option': 'A'}, {'selected_option': 'B'}, {'selected_option': 'A'}
    ]
    mock_options = ['A', 'B', 'C']
    outcome, counts = _tally_proposal_votes(mock_votes, mock_options)
    assert outcome == 'A'
    assert counts['A'] == 2
    assert counts['B'] == 1
```

**Key Tips for Testing:**

*   **Iterate:** Test features as you build them, not just at the very end.
*   **Logging:** Use Python's `logging` module extensively. `logger.info()`, `logger.debug()`, `logger.error()` will be invaluable for seeing what your bot is doing internally, especially when it's running on a server.
*   **Clean State:** Ensure you can easily reset your test database and vector store between test runs for consistent results.
*   **Patience:** Testing interactive systems like bots can be time-consuming but is crucial for a good user experience.
