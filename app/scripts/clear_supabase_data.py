import asyncio
import logging
import sys
import os

# Adjust PYTHONPATH to allow finding the 'app' module when running the script directly
# This adds the project root directory (e.g., 'telegram-voting-bot/') to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import AsyncSessionLocal # Engine is configured on import via ConfigService
from app.persistence.models.document_model import Document
from app.persistence.models.proposal_model import Proposal
from app.persistence.models.submission_model import Submission # Uncommented
from app.config import ConfigService # Explicitly load to ensure .env is processed if needed

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def clear_data_from_tables():
    logger.info("Attempting to clear data from Supabase tables: documents, proposals, submissions.")
    
    # Ensure .env variables are loaded, which configures the DATABASE_URL used by the engine
    _ = ConfigService()

    async with AsyncSessionLocal() as session:
        async with session.begin(): # Begin a transaction
            # Delete from Document table first due to potential FK constraints
            # (Document.proposal_id references Proposal.id)
            logger.info("Deleting all rows from 'documents' table...")
            stmt_documents = delete(Document)
            result_documents = await session.execute(stmt_documents)
            logger.info(f"Deleted {result_documents.rowcount} rows from 'documents' table.")

            # Delete from Submission table (before Proposal due to FK constraint)
            logger.info("Deleting all rows from 'submissions' table...")
            stmt_submissions = delete(Submission)
            result_submissions = await session.execute(stmt_submissions)
            logger.info(f"Deleted {result_submissions.rowcount} rows from 'submissions' table.")

            # Delete from Proposal table
            logger.info("Deleting all rows from 'proposals' table...")
            stmt_proposals = delete(Proposal)
            result_proposals = await session.execute(stmt_proposals)
            logger.info(f"Deleted {result_proposals.rowcount} rows from 'proposals' table.")
            
            # The transaction will be committed here upon exiting the `async with session.begin():` block
        logger.info("Data clearing process completed successfully.")

async def main_script_runner():
    print("\n" + "="*60)
    print("WARNING: THIS SCRIPT WILL DELETE ALL DATA FROM THE FOLLOWING TABLES:")
    print("  - documents")
    print("  - submissions")
    print("  - proposals")
    print("This operation is irreversible.")
    print("="*60 + "\n")
    
    confirm = input("Are you ABSOLUTELY SURE you want to continue? (yes/no): ")
    if confirm.lower() == 'yes':
        logger.info("User confirmed. Proceeding with data deletion.")
        try:
            await clear_data_from_tables()
        except Exception as e:
            logger.error(f"An error occurred during data clearing: {e}", exc_info=True)
            print(f"An error occurred: {e}")
    else:
        logger.info("Operation cancelled by the user.")
        print("Operation cancelled.")

if __name__ == "__main__":
    asyncio.run(main_script_runner()) 