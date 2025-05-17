import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.persistence.database import Base
from app.persistence.models.user_model import User # To establish ForeignKey

class ProposalType(enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    FREE_FORM = "free_form"

class ProposalStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    proposer_telegram_id = Column(Integer, ForeignKey(User.telegram_id), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    proposal_type = Column(String, nullable=False) # Using String to store enum values
    options = Column(JSON, nullable=True)  # For multiple_choice, stores list of option strings
    target_channel_id = Column(String, nullable=False) # ID of the channel proposal is for
    channel_message_id = Column(Integer, nullable=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deadline_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default=ProposalStatus.OPEN.value, nullable=False) # Using String for enum
    outcome = Column(Text, nullable=True) # Winning option for MC, summary for FF
    raw_results = Column(JSON, nullable=True) # Vote counts for MC, list of submissions for FF

    proposer = relationship("User")

    def __repr__(self):
        return f"<Proposal(id={self.id}, title='{self.title}', type='{self.proposal_type}', status='{self.status}')>" 