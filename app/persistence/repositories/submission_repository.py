import logging
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert # For INSERT ... ON CONFLICT DO UPDATE

from app.persistence.models.submission_model import Submission

logger = logging.getLogger(__name__)

class SubmissionRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def add_or_update_submission(
        self,
        proposal_id: int,
        submitter_id: int,
        response_content: str
    ) -> Optional[Submission]:
        """
        Adds a new submission or updates an existing one based on proposal_id and submitter_id.
        This implements an "upsert" functionality.
        Returns the Submission object if successful, None otherwise.
        """
        try:
            stmt = insert(Submission).values(
                proposal_id=proposal_id,
                submitter_id=submitter_id,
                response_content=response_content
            )
            # If a conflict occurs on (proposal_id, submitter_id), update response_content and timestamp
            # Note: server_default for timestamp on Submission model handles new inserts.
            # For updates, we might want to explicitly set timestamp = func.now() or rely on DB trigger if any.
            # For now, we'll update response_content. SQLAlchemy func.now() can be used for timestamp.
            # from sqlalchemy.sql import func # if needed here
            stmt = stmt.on_conflict_do_update(
                index_elements=['proposal_id', 'submitter_id'], # Matches UniqueConstraint name or columns
                set_=dict(response_content=response_content) # Update these fields on conflict
                # set_=dict(response_content=response_content, timestamp=func.now()) # If explicitly updating timestamp
            ).returning(Submission)
            
            result = await self.db_session.execute(stmt)
            await self.db_session.commit() # Commit after upsert
            submission = result.scalar_one_or_none()
            if submission:
                logger.info(f"Successfully added/updated submission for proposal {proposal_id} by user {submitter_id}")
            return submission
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error adding/updating submission for proposal {proposal_id}, user {submitter_id}: {e}", exc_info=True)
            return None

    async def get_submissions_for_proposal(self, proposal_id: int) -> List[Submission]:
        """
        Retrieves all submissions for a given proposal_id.
        Returns a list of Submission objects.
        """
        try:
            stmt = select(Submission).where(Submission.proposal_id == proposal_id).order_by(Submission.timestamp.desc())
            result = await self.db_session.execute(stmt)
            submissions = result.scalars().all()
            logger.info(f"Retrieved {len(submissions)} submissions for proposal {proposal_id}")
            return list(submissions)
        except Exception as e:
            logger.error(f"Error retrieving submissions for proposal {proposal_id}: {e}", exc_info=True)
            return [] 