from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.repositories.user_repository import UserRepository
from app.persistence.models.user_model import User

class UserService:
    def __init__(self, db_session: AsyncSession):
        self.user_repository = UserRepository(db_session)

    async def register_user_interaction(
        self, telegram_id: int, username: str | None, first_name: str | None
    ) -> User:
        """
        Registers or updates a user based on their interaction.
        Effectively an upsert based on telegram_id.
        """
        user = await self.user_repository.get_or_create_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        return user 

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        """Gets a user by their Telegram ID."""
        return await self.user_repository.get_user_by_telegram_id(telegram_id) 