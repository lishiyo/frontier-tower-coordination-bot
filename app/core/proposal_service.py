from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models.proposal_model import Proposal, ProposalType
from app.persistence.repositories.proposal_repository import ProposalRepository
# Removed UserRepository import as it's encapsulated by UserService
from app.core.user_service import UserService


class ProposalService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session # Retain for potential direct session use or pass to other components
        self.proposal_repository = ProposalRepository(db_session)
        self.user_service = UserService(db_session) # UserService now handles user interactions


    async def create_proposal(
        self,
        proposer_telegram_id: int,
        proposer_username: Optional[str],
        proposer_first_name: Optional[str],
        title: str,
        description: str,
        proposal_type: ProposalType,
        options: Optional[List[str]],
        deadline_date: datetime,
        target_channel_id: str,
    ) -> Proposal:
        """
        Creates a new proposal but does NOT commit the session.
        The calling handler/service is responsible for the commit.
        Ensures the proposer exists via UserService and then adds the proposal.
        """
        # Ensure proposer exists. UserService's register_user_interaction
        # handles the get_or_create logic. The underlying UserRepository
        # methods are designed not to commit, allowing service layer to control transactions.
        proposer = await self.user_service.register_user_interaction(
            telegram_id=proposer_telegram_id,
            username=proposer_username,
            first_name=proposer_first_name,
        )

        # Add the proposal using ProposalRepository
        # Note: ProposalRepository.add_proposal currently has its own commit.
        # This might be revisited for unified transaction management.
        new_proposal = await self.proposal_repository.add_proposal(
            proposer_telegram_id=proposer.telegram_id,
            title=title,
            description=description,
            proposal_type=proposal_type,
            options=options,
            deadline_date=deadline_date,
            target_channel_id=target_channel_id,
            # channel_message_id and status use defaults or are set later.
        )
        
        # No commit here. The caller (e.g., conversation handler) will commit.
        # await self.db_session.commit() # REMOVED

        return new_proposal 