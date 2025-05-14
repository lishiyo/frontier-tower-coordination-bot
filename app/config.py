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
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
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
        if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB]):
            raise ValueError("PostgreSQL configuration is incomplete in environment variables")
        return DATABASE_URL
    
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