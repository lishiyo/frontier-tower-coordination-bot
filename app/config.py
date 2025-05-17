import os
from typing import List

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# PostgreSQL configuration
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB")

# Database URL constructed from PostgreSQL config
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Admin IDs (comma-separated string)
ADMIN_TELEGRAM_IDS_STR = os.getenv("ADMIN_TELEGRAM_IDS", "")
ADMIN_TELEGRAM_IDS = [int(id_str.strip()) for id_str in ADMIN_TELEGRAM_IDS_STR.split(",") if id_str.strip()]

# Target channel ID where proposals will be posted
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID")

# Configuration class to provide easy access to all settings
class ConfigService:
    @staticmethod
    def get_bot_token() -> str:
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")
        return TELEGRAM_BOT_TOKEN
    
    @staticmethod
    def get_database_url() -> str:
        # Load environment variables within the method or ensure they are loaded at class/module level
        # For clarity, let's assume they are accessible here (e.g., as module-level variables after os.getenv)
        
        # It's better to load them directly here or ensure they are loaded by the class initializer
        # to avoid relying on global state if this class is instantiated elsewhere.
        # For this example, I'll assume they are available as module-level constants like shown above the class.
        
        user = POSTGRES_USER
        password = POSTGRES_PASSWORD
        host = POSTGRES_HOST
        port = POSTGRES_PORT
        db_name = POSTGRES_DB
        
        if not all([user, password, host, port, db_name]):
            missing_vars = []
            if not user: missing_vars.append("POSTGRES_USER")
            if not password: missing_vars.append("POSTGRES_PASSWORD")
            if not host: missing_vars.append("POSTGRES_HOST")
            if not port: missing_vars.append("POSTGRES_PORT")
            if not db_name: missing_vars.append("POSTGRES_DB")
            raise ValueError(f"PostgreSQL configuration is incomplete. Missing: {', '.join(missing_vars)}")

        # Construct the URL for asyncpg
        constructed_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
        
        return constructed_url
    
    @staticmethod
    def get_openai_api_key() -> str:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in environment variables")
        return OPENAI_API_KEY
    
    @staticmethod
    def get_admin_ids() -> List[int]:
        return ADMIN_TELEGRAM_IDS
    
    @staticmethod
    def get_target_channel_id() -> str:
        if not TARGET_CHANNEL_ID:
            raise ValueError("TARGET_CHANNEL_ID is not set in environment variables")
        return TARGET_CHANNEL_ID 