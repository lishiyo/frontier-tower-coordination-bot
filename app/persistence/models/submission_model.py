from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.persistence.database import Base

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False, index=True)
    submitter_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False, index=True)
    response_content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint('proposal_id', 'submitter_id', name='uq_proposal_submitter'),)

    def __repr__(self):
        return f"<Submission(id={self.id}, proposal_id={self.proposal_id}, submitter_id={self.submitter_id})>" 