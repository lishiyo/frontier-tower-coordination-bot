# CoordinationBot

A Telegram bot for policy proposals, voting, and contextual information at Frontier Tower.

## Overview

CoordinationBot is designed to facilitate community engagement through:
- Policy proposals (multiple-choice and free-form idea generation).
- Anonymous voting and submissions.
- Contextual information retrieval about proposals and policies (RAG).
- Future personalized voting recommendations.

This project is built with Python, `python-telegram-bot`, SQLAlchemy (with PostgreSQL), Alembic, ChromaDB, and the OpenAI API.

## Project Structure

(Refer to `memory-bank/systemPatterns.md` for a detailed architecture overview and directory structure.)

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd telegram-voting-bot
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On macOS/Linux
    # venv\Scripts\activate    # On Windows
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    *   Copy the `.env.example` file to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and fill in your actual credentials and configuration values:
        *   `TELEGRAM_BOT_TOKEN`: Your Telegram Bot token from BotFather.
        *   `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`: Your Supabase (or other PostgreSQL) database connection details. Use the connection pooler details from Supabase for best results.
        *   `OPENAI_API_KEY`: Your OpenAI API key.
        *   `ADMIN_TELEGRAM_IDS`: Comma-separated list of Telegram user IDs for admin commands.
        *   `TARGET_CHANNEL_ID`: The default Telegram channel ID where proposals will be posted.

5.  **Set up the database schema:**
    *   Ensure your database is running and accessible with the credentials in your `.env` file.
    *   Apply Alembic migrations to create the necessary tables:
        ```bash
        alembic upgrade head
        ```

## Usage

**Running the Bot:**

1.  Ensure your virtual environment is activated and environment variables (`.env`) are set.
2.  Start the bot:
    ```bash
    python main.py
    ```
    You should see log messages indicating the bot has started polling for updates.

Refer to [`bot_commands.md`](./memory-bank/bot_commands.md) for a list of all commands.

## Development

See [testing_instructions.md](memory-bank/testing_instructions.md) for how to test the bot.

**Clearing Database Data (for testing/reset):**

A script is provided to clear all data from the `documents` and `proposals` tables (and `submissions` in the future) in your Supabase database. This is useful for starting with a clean slate during development or testing.

1.  Ensure your virtual environment is activated.
2.  Run the script using one of the following commands from the project root directory (`telegram-voting-bot`):
    ```bash
    # Option 1: Run as a module (recommended)
    python -m app.scripts.clear_supabase_data

    # Option 2: Run directly
    python app/scripts/clear_supabase_data.py
    ```
3.  The script will ask for confirmation before deleting any data. Type `yes` to proceed.

    **WARNING:** This operation is irreversible and will delete all data in the specified tables. 