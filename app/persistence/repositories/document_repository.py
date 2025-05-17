from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.models.document_model import Document

class DocumentRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def add_document(
        self,
        title: Optional[str],
        content_hash: Optional[str],
        source_url: Optional[str],
        vector_ids: Optional[List[str]], # Assuming vector_ids from ChromaDB are strings
        proposal_id: Optional[int] = None,
    ) -> Document:
        """
        Adds a new document record to the database.
        `vector_ids` is a list of identifiers for the embeddings stored in the vector DB.
        """
        new_document = Document(
            title=title,
            content_hash=content_hash,
            source_url=source_url,
            vector_ids=vector_ids,
            proposal_id=proposal_id
            # upload_date is server_default
        )
        self.db_session.add(new_document)
        # The commit should ideally be handled by the service layer or calling handler
        # to manage transactions across multiple repository calls if needed.
        # For now, let's make this repository method commit itself for simplicity in this step.
        await self.db_session.commit()
        await self.db_session.refresh(new_document)
        return new_document 