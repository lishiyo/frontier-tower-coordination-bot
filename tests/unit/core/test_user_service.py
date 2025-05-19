import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.user_service import UserService
from app.persistence.repositories.user_repository import UserRepository # To mock its instance
from app.persistence.models.user_model import User # For type hinting and return values

@pytest.fixture
def mock_db_session(): # Although UserService takes db_session, it passes it to UserRepository
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def mock_user_repository_instance():
    return AsyncMock(spec=UserRepository)

@pytest.fixture
def user_service(mock_db_session, mock_user_repository_instance):
    # Patch the UserRepository where it's instantiated within UserService
    with patch('app.core.user_service.UserRepository', return_value=mock_user_repository_instance) as mock_user_repo_class:
        service = UserService(mock_db_session)
        # Ensure the service uses the provided mock instance if needed, or verify class was called.
        # In this case, UserService creates its own UserRepository instance.
        # So we check that the class was called with the session.
        mock_user_repo_class.assert_called_once_with(mock_db_session)
        # And we use the instance that the patch created for us if we need to mock its methods.
        service.user_repository = mock_user_repository_instance # Make sure our mock instance is used
        return service

@pytest.mark.asyncio
async def test_register_user_interaction(user_service: UserService, mock_user_repository_instance):
    # Arrange
    telegram_id = 123
    username = "testuser"
    first_name = "Test User"
    expected_user = User(id=1, telegram_id=telegram_id, username=username, first_name=first_name)

    mock_user_repository_instance.get_or_create_user = AsyncMock(return_value=expected_user)

    # Act
    user = await user_service.register_user_interaction(telegram_id, username, first_name)

    # Assert
    assert user == expected_user
    mock_user_repository_instance.get_or_create_user.assert_called_once_with(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name
    )

@pytest.mark.asyncio
async def test_register_user_interaction_no_username(user_service: UserService, mock_user_repository_instance):
    # Arrange
    telegram_id = 456
    username = None
    first_name = "Another User"
    expected_user = User(id=2, telegram_id=telegram_id, username=username, first_name=first_name)

    mock_user_repository_instance.get_or_create_user = AsyncMock(return_value=expected_user)

    # Act
    user = await user_service.register_user_interaction(telegram_id, username, first_name)

    # Assert
    assert user == expected_user
    mock_user_repository_instance.get_or_create_user.assert_called_once_with(
        telegram_id=telegram_id,
        username=None,
        first_name=first_name
    )

@pytest.mark.asyncio
async def test_register_user_interaction_no_firstname(user_service: UserService, mock_user_repository_instance):
    # Arrange
    telegram_id = 789
    username = "onlyusername"
    first_name = None
    expected_user = User(id=3, telegram_id=telegram_id, username=username, first_name=first_name)

    mock_user_repository_instance.get_or_create_user = AsyncMock(return_value=expected_user)

    # Act
    user = await user_service.register_user_interaction(telegram_id, username, first_name)

    # Assert
    assert user == expected_user
    mock_user_repository_instance.get_or_create_user.assert_called_once_with(
        telegram_id=telegram_id,
        username=username,
        first_name=None
    ) 