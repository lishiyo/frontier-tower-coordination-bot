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

1. Send the `/help` command to your bot
2. Expected result:
   - The bot should respond with a comprehensive help message that includes:
     - General commands section (`/start`, `/help`, `/privacy`)
     - Proposals & Voting section with command descriptions
     - Information section for `/ask` commands
     - Admin commands section
     - A reminder to use DM for most commands
   - Check your terminal; you should see a log entry showing a user requested help

## 5. Verify Formatting

1. Check that the formatting in both command responses appears properly in Telegram:
   - Line breaks should render correctly
   - Bold text for section headers should be visible
   - Command examples should be readable and clearly distinguished

## 6. Error Handling

1. Test with a non-existent command (e.g., `/nonexistent`)
   - The bot may not respond (expected at this stage as we haven't implemented a fallback handler)
   - Verify this doesn't crash the bot - check your terminal logs

## 7. Troubleshooting

If the bot doesn't respond or you encounter errors:

1. Check the terminal running the bot for error messages
2. Verify your bot token is correct in the `.env` file
3. Make sure there are no pending changes/edits in your code
4. Verify that your Python environment has all the required packages
5. If necessary, restart the bot (`Ctrl+C` to stop, then run `python main.py` again)

## 8. Test Cleanup

1. After testing, stop the bot by pressing `Ctrl+C` in your terminal
2. Verify the shutdown sequence log messages appear

## 9. Testing `/propose` Command

1. **Basic Command Format**
   - Send the `/propose` command with proper arguments:
     ```
     /propose Title; Description; Option1, Option2, Option3
     ```
     **OR**
     ```
     /propose Title; Description; FREEFORM
     ```
   - Example (Multiple Choice):
     ```
     /propose Community Lunch; What should we order for next week's lunch?; Pizza, Sushi, Salad, Sandwiches
     ```
   - Example (Free Form):
     ```
     /propose Project Ideas; Please share your ideas for our next project!; FREEFORM
     ```

2. **Expected Results for Multiple Choice Proposal**
   - The bot should send you a DM confirmation that includes:
     - The proposal ID
     - A preview of the proposal details
     - Information about the proposal being posted to the channel
   - The proposal should appear in the configured target channel with:
     - The title and description
     - Your name as the proposer
     - A deadline (currently 7 days from creation)
     - The provided options
     - (Note: Voting buttons will be implemented in a future task)

3. **Expected Results for Free Form Proposal**
   - The bot should send you a DM confirmation similar to multiple choice
   - The proposal should appear in the configured target channel with:
     - The title and description
     - Your name as the proposer
     - A deadline (currently 7 days from creation)
     - The proposal ID clearly displayed
     - Clear text instructions on how to submit ideas via DM (e.g., "To submit your idea, DM me (the bot) with: /submit [proposal_id] Your idea here")
     - (Note: The interactive "Submit Your Idea" button has been removed from channel messages due to Telegram API limitations for channel context.)

4. **Test Command Format Variations**
   - Test with missing arguments:
     ```
     /propose Just A Title
     ```
     Expected: The bot should respond with guidance on the correct format
   
   - Test with missing options in a multiple-choice proposal:
     ```
     /propose Title; Description
     ```
     Expected: The bot should interpret this as a free-form proposal or prompt for clarification

   - Test with very long titles/descriptions/options to verify proper handling

5. **Verify Logs and Database**
   - Check your terminal to see logs confirming proposal creation
   - Verify the proposal has been stored in the database (using application logs or direct database check if possible)
   - Confirm the channel message ID has been recorded (log should indicate this)

## 10. Testing Document Viewing Commands (Task 3.5)

These tests verify the functionality of document storage and viewing commands, primarily focusing on single-channel behavior as outlined in Task 3.5. You will need the `TARGET_CHANNEL_ID` from your `.env` file for some tests.

1.  **Preparation: Create a Proposal with Context**
    *   Use the `/propose` command conversationally to create a new proposal.
    *   When prompted for context, provide a short piece of text (e.g., "This is some sample context for testing document storage."). Note the content.
    *   Let the proposal creation complete. Note the `Proposal ID` and the `Document ID` if provided in confirmation messages or logs. (If Document ID isn't easily available, you might need to infer it from logs or by listing documents for the proposal in a later step).

2.  **Test `/view_doc <document_id>`**
    *   If you have a `Document ID` from the previous step, use it:
        ```
        /view_doc <your_document_id>
        ```
    *   **Expected Result:**
        *   The bot should DM you the raw content of the document.
        *   Verify this content matches what you provided during proposal creation.
        *   If the content is long, verify it's handled appropriately (e.g., sent in multiple messages or truncated with a notice).
    *   **Test with Invalid/Non-existent Document ID:**
        ```
        /view_doc 99999
        ```
    *   **Expected Result:** The bot should respond with a message indicating the document was not found or an error occurred.

3.  **Test `/view_docs` (No Arguments)**
    *   Send the command:
        ```
        /view_docs
        ```
    *   **Expected Result:**
        *   The bot should DM you a message indicating the current primary proposal channel, which should match your `TARGET_CHANNEL_ID` from the `.env` file. (e.g., "Proposals are currently managed in channel: [Your Target Channel ID]").

4.  **Test `/view_docs <channel_id>`**
    *   First, ensure you have at least one proposal created (e.g., the one from step 1).
    *   Send the command using your `TARGET_CHANNEL_ID`:
        ```
        /view_docs <your_target_channel_id>
        ```
    *   **Expected Result:**
        *   The bot should DM you a list of proposals associated with that channel.
        *   Verify the proposal(s) you created appear in this list (e.g., showing Proposal ID, title, status).
    *   **Test with an unauthorized/invalid Channel ID (Optional, if supported):**
        ```
        /view_docs <some_other_channel_id>
        ```
    *   **Expected Result:** The bot might indicate no proposals found or that the channel is not monitored, depending on implementation.

5.  **Test `/view_docs <proposal_id>`**
    *   Use the `Proposal ID` from the proposal you created in step 1.
        ```
        /view_docs <your_proposal_id>
        ```
    *   **Expected Result:**
        *   The bot should DM you a list of documents associated with that proposal.
        *   Verify the document you added as context (in step 1) is listed (e.g., showing Document ID and title).
    *   **Test with a Proposal ID that has no documents:**
        *   Create a new proposal without adding any context. Note its `Proposal ID`.
        *   Send `/view_docs <new_proposal_id_without_docs>`.
    *   **Expected Result:** The bot should indicate that no documents are associated with this proposal.
    *   **Test with an invalid/non-existent Proposal ID:**
        ```
        /view_docs 99999
        ```
    *   **Expected Result:** The bot should respond with a message indicating the proposal was not found or an error.

6.  **Verify Logs**
    *   Throughout these tests, monitor the bot's terminal logs for any errors or unexpected messages.
    *   Confirm that commands are being logged as executed.

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

