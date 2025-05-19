import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.config import ConfigService # Ensures .env is loaded by app.config module
from app.persistence.models.proposal_model import ProposalStatus, ProposalType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def add_embedding(args):
    """Adds a proposal embedding to the vector database."""
    try:
        llm_service = LLMService()
        vector_db_service = VectorDBService()
    except ValueError as e:
        logger.error(f"Error initializing services: {e}. Ensure OPENAI_API_KEY is set.")
        return

    proposal_text = f"{args.title} {args.description}"
    logger.info(f"Generating embedding for proposal ID {args.proposal_id}: \"{proposal_text[:100]}...\"")

    try:
        embedding = await llm_service.generate_embedding(proposal_text)
        if not embedding:
            logger.error("Failed to generate embedding.")
            return

        metadata = {
            "proposal_id": args.proposal_id,
            "status": args.status,
            "creation_date": args.creation_date if args.creation_date else datetime.utcnow().isoformat(),
            "deadline_date": args.deadline_date,
            "closed_date": args.closed_date,
            "proposal_type": args.proposal_type,
            "target_channel_id": args.target_channel_id
        }
        
        logger.info(f"Adding embedding to ChromaDB with metadata: {metadata}")
        await vector_db_service.add_proposal_embedding(
            proposal_id=args.proposal_id,
            text_content=proposal_text,
            embedding=embedding,
            metadata=metadata
        )
        logger.info(f"Successfully added embedding for proposal ID {args.proposal_id}.")

    except Exception as e:
        logger.error(f"Error during embedding addition: {e}", exc_info=True)

async def search_embeddings(args):
    """Searches proposal embeddings in the vector database."""
    try:
        llm_service = LLMService()
        vector_db_service = VectorDBService()
    except ValueError as e:
        logger.error(f"Error initializing services: {e}. Ensure OPENAI_API_KEY is set.")
        return

    logger.info(f"Generating embedding for search query: \"{args.query_text[:100]}...\"")
    
    try:
        query_embedding = await llm_service.generate_embedding(args.query_text)
        if not query_embedding:
            logger.error("Failed to generate embedding for the query.")
            return

        logger.info(f"Searching for top {args.top_n} proposals matching the query.")
        if args.proposal_ids:
            logger.info(f"Filtering by proposal IDs: {args.proposal_ids}")

        results = await vector_db_service.search_proposal_embeddings(
            query_embedding=query_embedding,
            top_n=args.top_n,
            filter_proposal_ids=args.proposal_ids
        )

        if results: # Check if the list is not empty
            logger.info("Search Results:")
            for hit in results: # Iterate through the list of hits
                p_id = hit.get("id", "N/A")
                doc_text = hit.get("document_content", "N/A")
                distance = hit.get("distance", "N/A")
                metadata = hit.get("metadata", {})
                
                # Ensure distance is formatted if it's a float
                distance_str = f"{distance:.4f}" if isinstance(distance, float) else str(distance)
                
                logger.info(f"  ID: {p_id}, Distance: {distance_str}")
                logger.info(f"     Text: {doc_text[:150] if doc_text else 'N/A'}...")
                logger.info(f"     Metadata: {metadata}")
        else:
            logger.info("No results found or empty results list.")
            # Optional: Log the raw results if it's an empty list but not None, for debugging
            if results == []:
                 logger.info("Raw results: [] (empty list)")

    except Exception as e:
        logger.error(f"Error during embedding search: {e}", exc_info=True)

async def main():
    """
    This script is used to test the proposal embeddings in ChromaDB.
    To use:
    1) python app/scripts/check_proposal_embeddings.py add --proposal_id 1 --title "Test Proposal" --description "This is a test proposal about a classroom polling system."
    2) python app/scripts/check_proposal_embeddings.py search "classroom polling system" --top_n 2
    """
    parser = argparse.ArgumentParser(description="CLI tool to test proposal embeddings in ChromaDB.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subparser for adding embeddings
    add_parser = subparsers.add_parser("add", help="Add a new proposal embedding.")
    add_parser.add_argument("--proposal_id", type=int, required=True, help="SQL ID of the proposal.")
    add_parser.add_argument("--title", type=str, required=True, help="Title of the proposal.")
    add_parser.add_argument("--description", type=str, required=True, help="Description of the proposal.")
    add_parser.add_argument("--status", type=str, default=ProposalStatus.OPEN.value, choices=[s.value for s in ProposalStatus], help="Proposal status.")
    add_parser.add_argument("--creation_date", type=str, help="Creation date (ISO format). Defaults to now.")
    add_parser.add_argument("--deadline_date", type=str, help="Deadline date (ISO format).")
    add_parser.add_argument("--closed_date", type=str, help="Closed date (ISO format).")
    add_parser.add_argument("--proposal_type", type=str, default=ProposalType.MULTIPLE_CHOICE.value, choices=[pt.value for pt in ProposalType], help="Proposal type.")
    add_parser.add_argument("--target_channel_id", type=str, help="Target channel ID for the proposal.")
    add_parser.set_defaults(func=add_embedding)

    # Subparser for searching embeddings
    search_parser = subparsers.add_parser("search", help="Search for proposal embeddings.")
    search_parser.add_argument("query_text", type=str, help="Text to search for.")
    search_parser.add_argument("--top_n", type=int, default=3, help="Number of top results to return.")
    search_parser.add_argument("--proposal_ids", type=int, nargs='*', help="Optional list of proposal SQL IDs to filter by.")
    search_parser.set_defaults(func=search_embeddings)

    args = parser.parse_args()
    await args.func(args)

if __name__ == "__main__":
    asyncio.run(main()) 