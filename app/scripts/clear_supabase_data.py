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
from app.services.vector_db_service import VectorDBService, DEFAULT_COLLECTION_NAME, PROPOSALS_COLLECTION_NAME # Added PROPOSALS_COLLECTION_NAME

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def clear_data_from_tables():
    logger.info("Attempting to clear data from Supabase tables and ChromaDB vector store.")
    
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
        logger.info("SQL data clearing process completed.")

    # Clear ChromaDB vector store data
    try:
        logger.info(f"Attempting to delete ChromaDB collection: {DEFAULT_COLLECTION_NAME}...")
        vdb_service = VectorDBService() # Assumes default path CHROMA_DATA_PATH
        if vdb_service.client:
            vdb_service.client.delete_collection(name=DEFAULT_COLLECTION_NAME)
            logger.info(f"Successfully deleted ChromaDB collection: {DEFAULT_COLLECTION_NAME}.")
        else:
            logger.error(f"VectorDBService client not initialized. Cannot delete ChromaDB collection: {DEFAULT_COLLECTION_NAME}.")
    except Exception as e:
        # Log error but don't let it stop the script if SQL part was successful
        # ChromaDB might raise an exception if the collection doesn't exist, which is fine.
        logger.warning(f"Could not delete ChromaDB collection '{DEFAULT_COLLECTION_NAME}' (it might not exist or another error occurred): {e}")

    try:
        logger.info(f"Attempting to delete ChromaDB collection: {PROPOSALS_COLLECTION_NAME}...")
        vdb_service = VectorDBService() # Re-initialize or ensure client is available
        if vdb_service.client:
            vdb_service.client.delete_collection(name=PROPOSALS_COLLECTION_NAME)
            logger.info(f"Successfully deleted ChromaDB collection: {PROPOSALS_COLLECTION_NAME}.")
        else:
            logger.error(f"VectorDBService client not initialized. Cannot delete ChromaDB collection: {PROPOSALS_COLLECTION_NAME}.")
    except Exception as e:
        logger.warning(f"Could not delete ChromaDB collection '{PROPOSALS_COLLECTION_NAME}' (it might not exist or another error occurred): {e}")

    logger.info("Data clearing process fully completed.")

async def main_script_runner():
    print("\n" + "="*60)
    print("WARNING: THIS SCRIPT WILL DELETE ALL DATA FROM THE FOLLOWING SQL TABLES:")
    print("  - documents")
    print("  - submissions")
    print("  - proposals")
    print("AND WILL DELETE THE FOLLOWING VECTOR DATABASE COLLECTIONS:")
    print(f"  - {DEFAULT_COLLECTION_NAME}")
    print(f"  - {PROPOSALS_COLLECTION_NAME}")
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