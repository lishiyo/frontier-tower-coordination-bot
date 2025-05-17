import argparse
import asyncio
import logging
import os
import sys

# Ensure the app directory is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.vector_db_service import VectorDBService
# from app.core.services import AppServiceFactory # To initialize services correctly - not used for now

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="View stored document chunks from ChromaDB for a given SQL document ID.")
    parser.add_argument("sql_document_id", type=int, help="The SQL ID of the document whose chunks are to be viewed.")
    parser.add_argument("--collection", type=str, default="general_context", help="The ChromaDB collection name to query (default: general_context).")
    
    args = parser.parse_args()

    # Initialize services - AppServiceFactory might not be strictly needed if VectorDBService has no complex deps
    # but it's good practice if it might evolve or if other services were needed.
    # For simplicity here, if VectorDBService is self-contained enough, direct init is also fine.
    # Let's assume direct initialization of VectorDBService is okay for this script.
    # config_service = ConfigService() # If VectorDBService needed config
    # vector_db_service = VectorDBService(path=config_service.get_chroma_db_path()) # Example if path came from config

    vector_db_service = VectorDBService() # Uses default path

    if not vector_db_service.client:
        logger.error("Failed to initialize VectorDBService. Exiting.")
        return

    logger.info(f"Attempting to retrieve chunks for SQL document ID: {args.sql_document_id} from collection: {args.collection}")
    
    chunks = await vector_db_service.get_document_chunks(
        sql_document_id=args.sql_document_id,
        collection_name=args.collection
    )

    if chunks is None:
        logger.error(f"Failed to retrieve chunks for SQL document ID: {args.sql_document_id}. Check logs for details.")
    elif not chunks:
        logger.info(f"No chunks found for SQL document ID: {args.sql_document_id} in collection '{args.collection}'.")
    else:
        logger.info(f"Found {len(chunks)} chunk(s) for SQL document ID: {args.sql_document_id}:\n")
        for i, chunk_text in enumerate(chunks):
            print(f"--- Chunk {i+1} ---")
            print(chunk_text)
            print("--------------------\n")

if __name__ == "__main__":
    asyncio.run(main()) 