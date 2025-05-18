import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application
from app.persistence.database import AsyncSessionLocal
from app.core.proposal_service import ProposalService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")
_bot_app: Application = None

async def start_scheduler_async(application: Application):
    """Starts the APScheduler and stores the application instance."""
    global _bot_app
    _bot_app = application

    if not scheduler.running:
        try:
            add_deadline_check_job()
            scheduler.start()
            logger.info("APScheduler started successfully with jobs.")
        except Exception as e:
            logger.error(f"Error starting APScheduler: {e}", exc_info=True)
            raise
    else:
        logger.info("APScheduler is already running.")

def stop_scheduler():
    """Stops the APScheduler gracefully."""
    if scheduler.running:
        try:
            scheduler.shutdown()
            logger.info("APScheduler stopped successfully.")
        except Exception as e:
            logger.error(f"Error stopping APScheduler: {e}", exc_info=True)

async def check_proposal_deadlines_job():
    """Job to check for and process expired proposals."""
    logger.info("Running scheduled job: check_proposal_deadlines_job")
    if not _bot_app:
        logger.error("Bot application instance not available in check_proposal_deadlines_job. Skipping.")
        return

    async with AsyncSessionLocal() as session:
        try:
            proposal_service = ProposalService(session, bot_app=_bot_app)
            processed_proposals = await proposal_service.process_expired_proposals()
            if processed_proposals:
                logger.info(f"Deadline check job processed {len(processed_proposals)} proposals.")
            else:
                logger.info("Deadline check job found no proposals to process or an issue occurred.")
        except Exception as e:
            logger.error(f"Error in check_proposal_deadlines_job: {e}", exc_info=True)

def add_deadline_check_job():
    """Adds the proposal deadline checking job to the scheduler."""
    try:
        scheduler.add_job(
            check_proposal_deadlines_job, 
            'interval', 
            minutes=1,
            id="deadline_check_job", 
            replace_existing=True
        )
        logger.info(f"Job 'deadline_check_job' added to scheduler. Interval: 1 minute.")
    except Exception as e:
        logger.error(f"Error adding deadline_check_job to scheduler: {e}", exc_info=True)

# Example of how to add a job (will be done in Task 5.2)
# def add_my_job(func, *args, **kwargs):
#     """Adds a job to the scheduler."""
#     # Example: scheduler.add_job(func, 'interval', minutes=1, args=args, kwargs=kwargs)
#     pass 