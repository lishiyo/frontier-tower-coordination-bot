from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.models.document_model import Document
from sqlalchemy.future import select

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
        await self.db_session.flush()
        # The commit should ideally be handled by the service layer or calling handler
        # to manage transactions across multiple repository calls if needed.
        # For now, let's make this repository method commit itself for simplicity in this step.
        await self.db_session.refresh(new_document)
        return new_document

    async def link_document_to_proposal(self, document_id: int, proposal_id: int) -> Optional[Document]:
        """Links an existing document to a proposal by setting its proposal_id."""
        result = await self.db_session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalars().first()

        if document:
            document.proposal_id = proposal_id
            # The commit for this update should be handled by the calling service/handler
            # to ensure it's part of the overall transaction related to proposal creation.
            # However, if process_and_store_document (which calls add_document) already committed
            # the document, then this linking step might also need its own commit if done separately.
            # For now, let's assume the handler will commit after this call if it's part of a larger transaction.
            # To be safe for now and ensure the link is made if called standalone, I will add a commit here.
            # This is another point of refactoring for better transaction control.
            # await self.db_session.commit() # REMOVED
            # await self.db_session.refresh(document) # Can be called by handler after commit if needed.
            return document
        return None 