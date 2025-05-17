from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.persistence.database import Base
# Assuming Proposal model might be needed for ForeignKey, adjust if not directly linked in model def
# from app.persistence.models.proposal_model import Proposal 

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=True) # User-provided title or filename
    content_hash = Column(String, nullable=True, index=True) # Hash of document to avoid duplicates
    source_url = Column(String, nullable=True) # URL if applicable
    upload_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    vector_ids = Column(JSON, nullable=True) # List of IDs/references to vectors in ChromaDB
    
    # Foreign Key to proposals table, nullable as documents can be general context too
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=True, index=True)
    
    # Relationship (optional, if you need to access Document.proposal or Proposal.documents)
    # proposal = relationship("Proposal", back_populates="documents") # Requires back_populates on Proposal

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', proposal_id={self.proposal_id})>" 