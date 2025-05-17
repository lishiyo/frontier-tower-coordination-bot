from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound

from app.persistence.models.user_model import User

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(self, telegram_id: int, username: str | None, first_name: str | None) -> User:
        """Gets an existing user or creates a new one if not found."""
        try:
            result = await self.session.execute(
                select(User).filter(User.telegram_id == telegram_id)
            )
            user = result.scalar_one()
            # Update user info if it has changed
            if user.username != username or user.first_name != first_name:
                user.username = username
                user.first_name = first_name
                # self.session.add(user) # Not strictly necessary if user is already in session and mutated
                # await self.session.commit() # Commit should be handled by the service layer
                # await self.session.refresh(user) # Refresh if needed after commit

        except NoResultFound:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
            self.session.add(user)
            # await self.session.commit() # Commit should be handled by the service layer
            # await self.session.refresh(user) # Refresh if needed after commit
        return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        """Gets a user by their Telegram ID."""
        result = await self.session.execute(
            select(User).filter(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none() 