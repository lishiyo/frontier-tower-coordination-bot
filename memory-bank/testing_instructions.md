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
     - A "Submit Your Idea" button (that prefills `/submit <proposal_id>` when clicked)

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

---

**Note:** This document will be expanded as more features are implemented.

