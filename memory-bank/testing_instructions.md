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

---

**Note:** This document will be expanded as more features are implemented.

