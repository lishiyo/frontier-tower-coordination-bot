from typing import List, Optional, Dict, Any, Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.persistence.models.proposal_model import Proposal, ProposalStatus, ProposalType
from datetime import datetime

class ProposalRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def add_proposal(
        self,
        proposer_telegram_id: int,
        title: str,
        description: str,
        proposal_type: ProposalType,
        deadline_date: datetime,
        target_channel_id: str,
        options: Optional[List[str]] = None,
        channel_message_id: Optional[int] = None,
        status: ProposalStatus = ProposalStatus.OPEN,
    ) -> Proposal:
        new_proposal = Proposal(
            proposer_telegram_id=proposer_telegram_id,
            title=title,
            description=description,
            proposal_type=proposal_type.value,
            options=options,
            target_channel_id=target_channel_id,
            channel_message_id=channel_message_id,
            deadline_date=deadline_date,
            status=status.value,
            # creation_date is server_default
            # outcome and raw_results are nullable and set later
        )
        self.db_session.add(new_proposal)
        await self.db_session.flush()
        await self.db_session.refresh(new_proposal)
        return new_proposal

    async def get_proposal_by_id(self, proposal_id: int) -> Optional[Proposal]:
        result = await self.db_session.execute(
            select(Proposal).where(Proposal.id == proposal_id).options(selectinload(Proposal.proposer))
        )
        return result.scalar_one_or_none()

    async def update_proposal_message_id(self, proposal_id: int, message_id: int) -> Optional[Proposal]:
        proposal = await self.get_proposal_by_id(proposal_id)
        if proposal:
            proposal.channel_message_id = message_id
            await self.db_session.flush()
            await self.db_session.refresh(proposal)
        return proposal

    async def find_expired_open_proposals(self) -> List[Proposal]:
        """Finds proposals that are currently open but past their deadline."""
        now = datetime.utcnow() # Consider timezone if deadline_date is timezone-aware
        # If deadline_date is stored as UTC, this is fine.
        # If it's timezone-aware, ensure 'now' is also timezone-aware or convert for comparison.
        # For simplicity assuming deadline_date is naive UTC or comparison handles it.
        # SQLAlchemy DateTime(timezone=True) stores timezone-aware datetimes.
        # func.now() in postgres is timezone-aware (defaults to session timezone or UTC)
        # Python's datetime.utcnow() is naive. Let's use timezone aware now.
        from sqlalchemy.sql import func # Re-import if not available in scope
        
        stmt = select(Proposal).where(
            Proposal.status == ProposalStatus.OPEN.value,
            Proposal.deadline_date < func.now() # func.now() is typically UTC in PG
        )
        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def update_proposal_status(
        self, proposal_id: int, status: ProposalStatus, outcome: Optional[str] = None, raw_results: Optional[Dict[str, Any]] = None
    ) -> Optional[Proposal]:
        """Updates the status, outcome, and raw_results of a proposal."""
        values_to_update = {"status": status.value}
        if outcome is not None:
            values_to_update["outcome"] = outcome
        if raw_results is not None:
            values_to_update["raw_results"] = raw_results
        
        stmt = (
            update(Proposal)
            .where(Proposal.id == proposal_id)
            .values(**values_to_update)
            .returning(Proposal)
        )
        result = await self.db_session.execute(stmt)
        await self.db_session.commit()
        return result.scalar_one_or_none()

    async def get_proposals_by_status(self, status: ProposalStatus) -> List[Proposal]:
        stmt = select(Proposal).where(Proposal.status == status.value).order_by(Proposal.creation_date.desc())
        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def get_proposals_by_ids(self, proposal_ids: List[int]) -> List[Proposal]:
        if not proposal_ids:
            return []
        stmt = select(Proposal).where(Proposal.id.in_(proposal_ids))
        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def update_proposal_details(
        self, 
        proposal_id: int, 
        title: Optional[str] = None, 
        description: Optional[str] = None, 
        options: Optional[List[str]] = None,
        deadline_date: Optional[datetime] = None
    ) -> Optional[Proposal]:
        values_to_update = {}
        if title is not None:
            values_to_update["title"] = title
        if description is not None:
            values_to_update["description"] = description
        if options is not None: # For multiple choice, could be empty list to clear
            values_to_update["options"] = options
        if deadline_date is not None:
            values_to_update["deadline_date"] = deadline_date

        if not values_to_update:
            return await self.get_proposal_by_id(proposal_id) # No changes

        stmt = (
            update(Proposal)
            .where(Proposal.id == proposal_id)
            .values(**values_to_update)
            .returning(Proposal)
        )
        result = await self.db_session.execute(stmt)
        await self.db_session.commit()
        return result.scalar_one_or_none()

    async def get_proposals_by_channel_id(self, channel_id: str) -> List[Proposal]:
        """Fetches proposals by their target_channel_id."""
        # Ensure channel_id is treated as a string if it comes in as a number from Telegram API
        stmt = select(Proposal).where(Proposal.target_channel_id == str(channel_id)).order_by(Proposal.creation_date.desc())
        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def get_proposals_by_proposer_id(self, proposer_telegram_id: int) -> List[Proposal]:
        """Fetches proposals by their proposer_telegram_id, ordered by creation_date descending."""
        stmt = (
            select(Proposal)
            .where(Proposal.proposer_telegram_id == proposer_telegram_id)
            .order_by(Proposal.creation_date.desc())
        )
        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def get_proposals_by_status(self, status: str) -> Sequence[Proposal]:
        """Fetches proposals from the database by their status."""
        query = select(Proposal).where(Proposal.status == status).order_by(Proposal.deadline_date.desc())
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def find_proposals_by_dynamic_criteria(
        self,
        status: Optional[str] = None,
        deadline_date_range: Optional[tuple[datetime, datetime]] = None, # Renamed from date_range for clarity
        creation_date_range: Optional[tuple[datetime, datetime]] = None,
        proposal_type: Optional[str] = None,
        proposer_telegram_id: Optional[int] = None,
        target_channel_id: Optional[str] = None
    ) -> List[Proposal]:
        """
        Finds proposals based on a dynamic set of criteria.
        All provided criteria are ANDed together.
        """
        stmt = select(Proposal)

        if status:
            stmt = stmt.where(Proposal.status == status)
        
        if deadline_date_range:
            start_date, end_date = deadline_date_range
            if start_date:
                stmt = stmt.where(Proposal.deadline_date >= start_date)
            if end_date:
                stmt = stmt.where(Proposal.deadline_date <= end_date)

        if creation_date_range:
            start_date, end_date = creation_date_range
            if start_date:
                stmt = stmt.where(Proposal.creation_date >= start_date)
            if end_date:
                stmt = stmt.where(Proposal.creation_date <= end_date)

        if proposal_type:
            # Assuming proposal_type in the model is stored as the string value (e.g., "MULTIPLE_CHOICE")
            # If it's stored as ProposalType.MULTIPLE_CHOICE.value, this is correct.
            stmt = stmt.where(Proposal.proposal_type == proposal_type)

        if proposer_telegram_id is not None: # Check for None explicitly for integer 0
            stmt = stmt.where(Proposal.proposer_telegram_id == proposer_telegram_id)
        
        if target_channel_id:
            stmt = stmt.where(Proposal.target_channel_id == target_channel_id)
            
        # Default ordering, can be parameterized later if needed
        stmt = stmt.order_by(Proposal.creation_date.desc())

        result = await self.db_session.execute(stmt)
        return list(result.scalars().all()) 