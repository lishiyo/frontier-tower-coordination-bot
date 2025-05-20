# Manual Testing Instructions

## 1. Prerequisites

Before testing, ensure you have:
1. A Telegram account
2. A test bot token from BotFather
3. Properly set up your `.env` file with the test bot token
4. Installed all dependencies from `requirements.txt`

## 2. Starting the Bot for Testing

1. Ensure your virtual environment is activated:
   ```
   source venv/bin/activate  # On macOS/Linux
   venv\Scripts\activate     # On Windows
   ```

2. Run the bot:
   ```
   python main.py
   ```

3. You should see log messages indicating the bot has started successfully:
   ```
   INFO - Bot application created and command handlers registered.
   INFO - Starting bot polling...
   ```

## 3. Testing `/start` Command

1. Open Telegram and find your test bot using the username you registered with BotFather
2. Send the `/start` command to your bot
3. Expected result:
   - The bot should respond with a welcome message that includes:
     - A personalized greeting with your first name
     - An introduction to what the bot can do (proposals, voting, information)
     - A brief list of key commands
     - A prompt to use `/help` for more information
   - Check your terminal running the bot; you should see a log entry showing a user initiated the bot with the `/start` command

## 4. Testing `/help` Command

1.  **Basic `/help`**
    *   Send the `/help` command to your bot.
    *   **Expected Result:**
        *   The bot should respond with a comprehensive help message that includes:
            *   General commands section (`/start`, `/help`, `/privacy`)
            *   Proposals & Voting section with command descriptions
            *   Information section for `/ask` commands
            *   Admin commands section
            *   A reminder to use DM for most commands
        *   Check your terminal; you should see a log entry showing a user requested help.

2.  **Intelligent `/help <question>` (Task 9.4)**
    *   Send a question to the help command, e.g.:
        ```
        /help how do I create a proposal?
        /help what's the command to see my votes?
        /help how to add context to a proposal I made?
        ```
    *   **Expected Result:**
        *   The bot should respond with a natural language explanation based on `bot_commands.md`.
        *   The response should suggest relevant commands.
        *   Verify if the bot includes interactive buttons for the suggested commands.
        *   If the question is too vague or unanswerable from `bot_commands.md`, the bot should provide a polite message indicating it couldn't find a specific answer or might suggest trying a broader query.
    *   Check terminal logs for any errors during LLM processing.

## 5. Verify Formatting

1. Check that the formatting in all command responses appears properly in Telegram:
   - Line breaks should render correctly
   - Bold text for section headers should be visible
   - Command examples should be readable and clearly distinguished
   - Inline buttons should be clearly labeled and functional.

## 6. Error Handling

1. Test with a non-existent command (e.g., `/nonexistent`)
   - The bot may not respond (expected at this stage as we haven't implemented a fallback handler for completely unknown commands) or might give a generic "command not understood" if such a handler exists.
   - Verify this doesn't crash the bot - check your terminal logs.
2. Test commands with incorrect argument formats (e.g., `/propose just_a_title_no_semicolon`) and verify helpful error messages are provided.

## 7. Troubleshooting

If the bot doesn't respond or you encounter errors:

1. Check the terminal running the bot for error messages.
2. Verify your bot token is correct in the `.env` file.
3. Make sure there are no pending changes/edits in your code.
4. Verify that your Python environment has all the required packages.
5. If necessary, restart the bot (`Ctrl+C` to stop, then run `python main.py` again).

## 8. Test Cleanup

1. After testing, stop the bot by pressing `Ctrl+C` in your terminal.
2. Verify the shutdown sequence log messages appear.

## 9. Testing `/propose` Command (Conversational Flow - Task 3.4)

1.  **Basic Command Format & Conversational Fallback**
    *   Test sending `/propose` with varying levels of initial information:
        *   Just `/propose` -> trigger full flow (title, description, multiple-choice or freeform, options, duration, docs)
        *   `/propose My Event Proposal` -> trigger from description onwards
        *   make freeform proposal: `/propose Weekend Hackathon; Let's build something cool!; FREEFORM` -> trigger duration, docs
        *   make multiple-choice proposal: `/propose Team Lunch Plan; Decide on next week's lunch; Pizza, Sushi, Salad` -> trigger duration, docs
    *   **Expected Result (for all variations):**
        *   The bot should initiate a DM conversation if not already in one.
        *   It should sequentially ask for any missing core details: Title, Description, Proposal Type (Multiple Choice or Free Form), Options (if MC).
        *   Verify the prompts are clear.
        *   (Multi-channel if configured) If in DM and multi-channel is active, it should ask to select a target channel.
        *   It should then ask for the duration (e.g., "How long should this proposal be open?").
        *   Test natural language durations (e.g., "for 3 days", "until next Monday at 5pm"). Verify LLM parsing and confirmation if ambiguous.
        *   It should then ask for initial context ("Do you have any extra context... You can paste text, provide a URL, or just say 'no'").
        *   Test providing text context, a URL, and saying "no".
        *   Upon completion, the bot should send a DM confirmation with the proposal ID and channel information.
        *   The proposal should appear in the configured target channel, formatted correctly.
        *   Free-form proposals in the channel should have the "💬 Submit Your Idea" button prefilling `/submit <proposal_id>`.
        *   Multiple-choice proposals should have inline voting buttons.

2.  **In-Channel Initiation (if multi-channel configured and channel is authorized)**
    *   Type `/propose My Channel Proposal` in an authorized Telegram channel.
    *   **Expected Result:**
        *   The bot should send a DM to you to continue the setup (duration, context).
        *   The final proposal should be posted back to the channel where `/propose` was initiated.

3.  **Test Command Format Variations (within conversational flow if initial structured command was incomplete)**
    *   Ensure that if the user provides partial info, the conversation picks up correctly.

4.  **Verify Logs and Database**
    *   Check terminal logs for proposal creation, LLM calls for duration, context processing.
    *   Verify the proposal is stored in the database with correct details (title, description, type, options, proposer_id, target_channel_id, deadline_date, status="open").
    *   If context was added, verify a `Document` record is created, linked to the proposal, and `raw_content` is stored. Check for vector DB indexing logs.
    *   Confirm `channel_message_id` is recorded for the proposal.

## 10. Testing Document Storage & Viewing Commands (Tasks 3.5, 9.2)

These tests verify document storage, viewing, and multi-channel listing capabilities.

1.  **Preparation: Create Proposals with Context**
    *   Create at least two proposals using the conversational `/propose` flow.
    *   For Proposal A (in Channel 1, if multi-channel): Add text context (e.g., "Detailed rules for event A."). Note the content.
    *   For Proposal B (in Channel 2, if multi-channel, otherwise same channel): Add URL context (e.g., a link to a public document). Note the URL.
    *   Note the `Proposal ID`s and `Document ID`s if provided, or infer from logs/later listing.

2.  **Test `/view_doc <document_id>` (Task 3.5)**
    *   Use a `Document ID` from one of the proposals created above.
        ```
        /view_doc <your_document_id>
        ```
    *   **Expected Result:**
        *   Bot DMs you the raw content. Verify it matches the text or fetched URL content.
        *   If content is long, check handling.
    *   **Test "Missing ID" Flow (Task 9.5.3):**
        *   Send `/view_doc` without an ID.
        *   **Expected Result:** Bot messages "Which doc? Use `/ask 'which doc mentioned...'` to search for the doc ID, then use `/view_doc <document_id>`." It should include an inline button "Search for Documents".
        *   Tap the "Search for Documents" button.
        *   **Expected Result:** The bot should send a message with instructions on how to use `/ask` to find document IDs, including examples, and a "Close" button.

3.  **Test `/view_docs` (Multi-Channel Document Viewing - Task 9.2)**
    *   **`/view_docs` (No Arguments):**
        *   Send the command: `/view_docs`
        *   **Expected Result:**
            *   If single-channel mode: Message indicating the `TARGET_CHANNEL_ID`.
            *   If multi-channel mode: Lists all authorized channels (ID and Name if available) with buttons for each that prefill `/view_docs <channel_id>`.
    *   **`/view_docs <channel_id>`:**
        *   Use an authorized `channel_id`.
        *   **Expected Result:**
            *   Lists proposals in that channel (ID, title, status) with buttons for each that prefill `/view_docs <proposal_id>`.
    *   **`/view_docs <proposal_id>`:**
        *   Use a `proposal_id` that has associated documents.
        *   **Expected Result:**
            *   Lists documents for that proposal (ID, title) with buttons for each that prefill `/view_doc <document_id>`.
    *   **Test with a Proposal ID that has no documents:**
        *   Create a proposal without context. Send `/view_docs <new_proposal_id>`.
        *   **Expected Result:** Bot indicates no documents are associated.
    *   **Test with invalid/non-existent IDs** for channel and proposal.
        *   **Expected Result:** Appropriate "not found" or error messages.

4.  **Verify Logs**
    *   Monitor logs for document processing (chunking, embedding), URL fetching, and command execution.

## 11. Testing Voting and Submission (Task 4.1, 4.2, 4.3)

1.  **Multiple-Choice Voting (Task 4.2)**
    *   Create a multiple-choice proposal with a reasonable deadline (e.g., 5-10 minutes).
    *   In the channel, click one of the voting option buttons.
    *   **Expected Result:** Receive an ephemeral confirmation (e.g., "Your vote for 'Option X' has been recorded!").
    *   Click a *different* option button for the same proposal.
    *   **Expected Result:** Receive confirmation that your vote has been updated.
    *   Verify in logs/database that the submission is correctly recorded/updated with the chosen option string.

2.  **Free-Form Submission (Task 4.3)**
    *   Create a free-form proposal with a reasonable deadline.
    *   Note its `Proposal ID`.
    *   Use the "💬 Submit Your Idea" button on the channel message.
    *   **Expected Result:** Your DM chat with the bot should prefill with `@BotUsername /submit <proposal_id> `.
    *   Complete the command by adding your submission text and send it (e.g., `/submit <proposal_id> This is my great idea.`).
    *   **Expected Result:** Receive a DM confirmation ("Your submission for proposal #X has been recorded.").
    *   Send another submission for the same proposal: `/submit <proposal_id> This is my updated idea.`.
    *   **Expected Result:** Receive confirmation that your submission has been updated.
    *   Verify in logs/database that the submission is correctly recorded/updated.

## 12. Testing Deadline Processing & Results Announcement (Task 5.1, 5.2, 5.3)

This section remains largely the same as the original, but ensure to verify:
*   **Free-Form Results (Task 5.3):** The channel message for closed free-form proposals should include the LLM-generated summary of submission clusters.
*   Test `/view_results <ff_proposal_id>` DMs you the full list of anonymized submissions.

## 13. Testing User History Commands (Task 7.1, 7.2, 9.5.5)

1.  **Preparation:**
    *   As a test user, create a proposal.
    *   Vote on a multiple-choice proposal.
    *   Submit to a free-form proposal.

2.  **Test `/my_votes` (or `/my_submissions`) (Task 7.1)**
    *   Send `/my_votes`.
    *   **Expected Result:** A DM listing the proposals you voted on/submitted to, your response, and the proposal's status/outcome. Verify formatting and accuracy.

3.  **Test `/my_proposals` (Task 7.2)**
    *   Send `/my_proposals`.
    *   **Expected Result:** A DM listing proposals you created, with ID, title, status, deadline/outcome, and target channel. Verify formatting and accuracy.

4.  **Test `/my_vote <proposal_id>` (Task 9.5.5)**
    *   Use a `proposal_id` for which you have submitted a vote/response.
        ```
        /my_vote <your_voted_proposal_id>
        ```
    *   **Expected Result:** A DM showing your specific vote/submission for that proposal (e.g., "For proposal 'Team Lunch Plan', your submission was: 'Pizza'.").
    *   **Test "Missing ID" Flow:**
        *   Send `/my_vote` without an ID.
        *   **Expected Result:** Bot messages "Which proposal? You can see all open and closed proposals for their ids." with buttons for "Open Proposals" and "Closed Proposals" (which should trigger `/proposals open` and `/proposals closed` respectively) and a "Search with /ask" button.
        *   Tap the "Search with /ask" button.
        *   **Expected Result:** The bot should send a message with instructions on how to use `/ask "which proposal was about..."` to find proposal IDs, and a "Close" button.

## 14. Testing Proposal Listing and Management Commands (Task 7.3, 7.4, 7.5, 9.5.4)

1.  **Test `/proposals`, `/proposals open`, `/proposals closed` (Task 7.3)**
    *   Send `/proposals open`.
    *   **Expected Result:** DM listing open proposals (title, deadline).
    *   Send `/proposals closed`.
    *   **Expected Result:** DM listing closed proposals (title, outcome).
    *   Send `/proposals` without arguments.
    *   **Expected Result:** Bot DMs "Open or closed?" with inline buttons "Open Proposals" and "Closed Proposals". Tapping these should behave like `/proposals open` and `/proposals closed`.

2.  **Test `/view_proposal <proposal_id>` (Task 9.5.4)**
    *   Create a proposal and note its ID and the channel it was posted to.
    *   Send `/view_proposal <that_proposal_id>`.
    *   **Expected Result:** Bot DMs a direct link to the proposal message in its channel. Tapping the link should take you to that message.
    *   Test with a public channel ID (e.g., `@channelusername`) and a private supergroup ID (e.g., `-100...`).
    *   **Test "Missing ID" Flow:**
        *   Send `/view_proposal` without an ID.
        *   **Expected Result:** Bot messages "Which proposal? Use `/my_proposals` to list your own, `/proposals open` or `/proposals closed` to see all, or `/ask 'which proposal was about...'` to find a proposal ID. Then use `/view_proposal <proposal_id>`." Buttons for relevant commands should be present.
        *   Tap the "Search with /ask" button from the prompt.
        *   **Expected Result:** The bot should send instructions on using `/ask "which proposal was about..."`, with a "Close" button.

3.  **Test `/edit_proposal <proposal_id>` (Proposer Only - Task 7.4)**
    *   As the proposer, create a new proposal. Do NOT vote on it. Note its ID.
    *   Send `/edit_proposal <proposal_id>`.
    *   **Expected Result:** Bot initiates a conversation to get new title, description, options. Complete this flow.
    *   Verify proposal details are updated in the database and the channel message is edited.
    *   **Test "Missing ID" Flow:**
        *   Send `/edit_proposal` without an ID.
        *   **Expected Result:** Bot messages "Which proposal? Use `/my_proposals` to list all or `/ask 'which proposal was about...'` to get a proposal ID. Then use `/edit_proposal <proposal_id>`." Buttons for `/my_proposals` and a "Search with /ask" button should be present.
        *   Tap the "Search with /ask" button.
        *   **Expected Result:** Bot sends instructions for using `/ask`.
    *   Create another proposal, vote on it, then try to edit it.
    *   **Expected Result:** Edit should be rejected with a message ("Cannot edit, votes/submissions exist.").

4.  **Test `/cancel_proposal <proposal_id>` (Proposer Only - Task 7.5)**
    *   As the proposer, create a new proposal. Note its ID.
    *   Send `/cancel_proposal <proposal_id>`.
    *   **Expected Result:** Proposal status changes to "cancelled". Channel message is updated. Confirmation DM sent.
    *   **Test "Missing ID" Flow:**
        *   Send `/cancel_proposal` without an ID.
        *   **Expected Result:** Bot messages "Which proposal? Use `/my_proposals` to list all or `/ask 'which proposal was about...'` to get a proposal ID. Then use `/cancel_proposal <proposal_id>`." Buttons for `/my_proposals` and a "Search with /ask" button.
        *   Tap the "Search with /ask" button.
        *   **Expected Result:** Bot sends instructions for using `/ask`.
    *   Try to cancel a proposal that is already closed or cancelled, or one you didn't propose.
    *   **Expected Result:** Appropriate error message.

## 15. Testing `/ask` Command (Enhanced RAG & Proposal Querying - Tasks 6.2, 9.5.2)

1.  **Preparation:**
    *   Ensure some global documents have been added by an admin (see Task 16).
    *   Ensure some proposals exist, with varying statuses (open, closed), types, and containing diverse keywords in titles/descriptions.
    *   Ensure some proposals have context documents added via `/add_doc`.

2.  **Test General Document RAG:**
    *   Ask a question that should be answered by a global document:
        ```
        /ask What are the community guidelines?
        ```
    *   **Expected Result:** Bot DMs an answer synthesized from the relevant global document, citing the source document. Buttons to view source documents should appear if relevant.

3.  **Test Proposal Querying (Structured Filters & Keywords):**
    *   Ask questions targeting proposals:
        *   Status: `/ask what proposals are open?`
        *   Type: `/ask show me free_form proposals`
        *   Date (Deadline): `/ask which proposals closed last week?`
        *   Date (Creation): `/ask what proposals were created this month?` (Verify creation_date is used for filtering AND is shown in summary if applicable).
        *   Keywords: `/ask any proposals about "budget"?`
        *   Combined: `/ask open proposals about "events" from this month`
    *   **Expected Result (for each):**
        *   Bot DMs a synthesized answer listing matching proposals (ID, Title, Status, Type, Creation Date, Deadline).
        *   The answer should guide the user to use `/my_vote <id>` or `/view_proposal <id>`.
        *   If context documents were found related to the query AND the matched proposals, their context should be summarized or used in the answer, and buttons to view these documents should appear.
        *   Verify logs to see if intent was `query_proposals` and if filters/keywords were extracted correctly.

4.  **Test `/ask` without a question:**
    *   Send `/ask`
    *   **Expected Result:** Bot provides guidance on how to use the `/ask` command effectively.

5.  **Test Ambiguous Queries:**
    *   Try a query that could be for general docs or proposals. Observe how the bot handles it (which intent it picks, or if it asks for clarification).

6.  **Test "Not Found" Scenarios:**
    *   Ask about proposals with criteria that won't match anything.
    *   **Expected Result:** Polite "couldn't find anything" message.

## 16. Testing Admin Document Management (Tasks 6.1, 8.4)

Requires an admin user (ID listed in `ADMIN_TELEGRAM_IDS`).

1.  **Test `/add_global_doc` (Task 6.1)**
    *   As admin, send `/add_global_doc <URL to a public document>`.
    *   As admin, send `/add_global_doc` then paste a paragraph of text when prompted (or if it supports direct text).
    *   **Expected Result:** Confirmation DM. Document processed and stored. Verify via logs and by asking a question related to its content using `/ask`.
    *   **Test with non-admin user:** Command should be rejected.

2.  **Test `/view_global_docs` (Task 8.4)**
    *   As admin, send `/view_global_docs`.
    *   **Expected Result:** DM listing global documents (ID, title).
    *   **Test with non-admin user:** Command should be rejected.

3.  **Test `/edit_global_doc <document_id>` (Task 8.4)**
    *   As admin, use an ID from `/view_global_docs`. Send `/edit_global_doc <id>`.
    *   Bot should prompt for new content/title. Provide new text.
    *   **Expected Result:** Confirmation DM. Document content updated. Verify by `/view_doc <id>` or by asking a question targeting the new content.
    *   **Test "Missing ID" Flow:** Send `/edit_global_doc` without ID. Expected prompt with `/view_global_docs` and `/ask` suggestions + buttons.
    *   **Test with non-admin user:** Command should be rejected.

4.  **Test `/delete_global_doc <document_id>` (Task 8.4)**
    *   As admin, use an ID. Send `/delete_global_doc <id>`.
    *   **Expected Result:** Confirmation DM. Document removed. Verify by trying to `/view_doc <id>` (should fail) or asking a question (should no longer find it).
    *   **Test "Missing ID" Flow:** Send `/delete_global_doc` without ID. Expected prompt.
    *   **Test with non-admin user:** Command should be rejected.

## 17. Testing Proposer Document Management (Tasks 8.2, 8.3)

1.  **Test `/add_doc <proposal_id>` (Task 8.2)**
    *   As a user, create a proposal. Note its ID.
    *   Send `/add_doc <your_proposal_id>` and provide text or a URL when prompted (or directly if supported).
    *   **Expected Result:** Confirmation DM. Document linked to your proposal. Verify with `/view_docs <your_proposal_id>` and by using `/ask <your_proposal_id> <question about the doc>`.
    *   **Test "Missing ID" Flow:** Send `/add_doc`. Expected prompt for proposal ID with `/my_proposals` and `/ask` suggestions + buttons.
    *   Try with a proposal ID you didn't create. **Expected Result:** Command rejected.

2.  **Test `/my_docs` (Task 8.1)**
    *   After adding docs via `/add_doc` to proposals you created, send `/my_docs`.
    *   **Expected Result:** DM listing documents you've added to your proposals (doc ID, title, associated proposal).

3.  **Test `/edit_doc <document_id>` (Task 8.3)**
    *   Use a `document_id` from `/my_docs` that you added to one of your proposals.
    *   Send `/edit_doc <document_id>`. Bot prompts for new content. Provide it.
    *   **Expected Result:** Confirmation. Document content updated. Verify.
    *   **Test "Missing ID" Flow:** Send `/edit_doc`. Expected prompt with `/my_docs` and `/ask` suggestions + buttons.
    *   Try with a document ID not yours or a global doc ID. **Expected Result:** Rejected.

4.  **Test `/delete_doc <document_id>` (Task 8.3)**
    *   Use a `document_id` from `/my_docs`. Send `/delete_doc <document_id>`.
    *   **Expected Result:** Confirmation. Document deleted. Verify.
    *   **Test "Missing ID" Flow:** Send `/delete_doc`. Expected prompt.
    *   Try with a document ID not yours. **Expected Result:** Rejected.

## 18. Testing `/privacy` Command (Task 8.6)

1. Send `/privacy`.
2. **Expected Result:** Bot DMs the privacy policy text.

---

**Note:** This document will be expanded as more features are implemented.

## 11. Testing Deadline Processing & Results Announcement (Task 5.1 & 5.2)

These tests verify that the scheduler correctly identifies expired proposals, processes their results, and posts them to the channel. The scheduler job interval is currently set to 1 minute for easier testing.

1.  **Preparation:**
    *   Ensure the bot is running. You should see logs indicating the APScheduler has started and the `deadline_check_job` is added.
    *   You will need at least two proposals: one multiple-choice and one free-form.

2.  **Create a Multiple-Choice Proposal with a Short Deadline:**
    *   Use the `/propose` command conversationally.
    *   For the duration, specify a very short time, e.g., "for 2 minutes" or "until [current time + 2 minutes]".
    *   Note the `Proposal ID` and the `Target Channel ID`.
    *   Have one or more test users (or yourself from different accounts if possible) vote on the options before the 2-minute deadline.
        *   Vote for different options to test tie-breaking and single winner scenarios.
        *   Consider a case where no one votes, or votes are only for one option.

3.  **Create a Free-Form Proposal with a Short Deadline:**
    *   Use the `/propose` command conversationally.
    *   Set the type to "Free Form".
    *   For the duration, specify a very short time, e.g., "for 3 minutes" or "until [current time + 3 minutes]".
    *   Note the `Proposal ID` and the `Target Channel ID`.
    *   Have one or more test users submit different free-form responses using the `/submit <proposal_id> <text>` command (or via the deep-link button flow) before the 3-minute deadline.
        *   Submit a few varied text responses.
        *   Consider a case where no one submits.

4.  **Observe Scheduler and Processing:**
    *   Monitor the bot's console logs.
    *   After the short deadlines pass, you should see logs from `SchedulingService` indicating `check_proposal_deadlines_job` is running.
    *   Subsequently, you should see logs from `ProposalService.process_expired_proposals` detailing its actions for each expired proposal:
        *   Fetching proposals.
        *   Calculating/summarizing results.
        *   Updating proposal status in the database.
        *   Attempting to post results to the channel.

5.  **Verify Results in Channel:**
    *   Check the target channel(s) where the proposals were originally posted.
    *   **For the Multiple-Choice Proposal:**
        *   A new message should be posted (replying to the original proposal) announcing the results.
        *   This message should state the winner(s) or if it was a tie, and include vote counts and percentages for each option.
        *   Verify the vote counts match the votes you cast.
    *   **For the Free-Form Proposal:**
        *   A new message should be posted (replying to the original proposal) announcing the results.
        *   This message should currently contain the placeholder summary (e.g., "Received X submission(s). Full list available via /view_results.").

6.  **Verify Database Updates:**
    *   (If you have database access) Check the `proposals` table for the processed proposals:
        *   Verify their `status` is now `CLOSED`.
        *   Verify the `outcome` field contains the summary text or winner information.
        *   Verify the `raw_results` field contains the vote counts (for MC) or the list of submission texts (for FF).

7.  **Test `/view_results <proposal_id>` for Closed Proposals:**
    *   For the multiple-choice proposal: `/view_results <mc_proposal_id>`
        *   Expected: Bot DMs you a breakdown of votes (similar to what was posted in the channel, but can be more detailed if designed so).
    *   For the free-form proposal: `/view_results <ff_proposal_id>`
        *   Expected: Bot DMs you the list of all anonymized free-form submissions that were part of `raw_results`.

8.  **Edge Cases/Further Tests:**
    *   Create a proposal and let it expire *without* any votes/submissions. Verify the outcome message is appropriate (e.g., "No votes cast.", "No submissions received.").
    *   If possible, stop and restart the bot *before* a proposal's short deadline to ensure the scheduler picks it up correctly after restart.
    *   Check log messages for any errors during processing or posting.

