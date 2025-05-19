import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.persistence.repositories.user_repository import UserRepository
from app.persistence.models.user_model import User

@pytest.fixture
def mock_session():
    ms = AsyncMock(spec=AsyncSession)
    # session.execute() returns a result object. This result object has scalar_one, scalar_one_or_none.
    # These scalar methods are synchronous on the result object.
    mock_result_object = MagicMock() # This will be returned by session.execute()
    ms.execute = AsyncMock(return_value=mock_result_object)
    return ms, mock_result_object # Return both for easy access in tests

@pytest.fixture
def user_repository(mock_session):
    # mock_session is now a tuple (session_mock, result_mock)
    return UserRepository(mock_session[0])

@pytest.mark.asyncio
async def test_get_or_create_user_exists_no_change(user_repository: UserRepository, mock_session):
    session_mock, result_mock = mock_session
    # Arrange
    telegram_id = 123
    username = "testuser"
    first_name = "Test"
    existing_user = User(id=1, telegram_id=telegram_id, username=username, first_name=first_name)

    result_mock.scalar_one.return_value = existing_user # scalar_one now returns the user directly

    # Act
    user = await user_repository.get_or_create_user(telegram_id, username, first_name)

    # Assert
    assert user == existing_user
    assert user.username == username
    assert user.first_name == first_name
    session_mock.execute.assert_called_once()
    session_mock.add.assert_not_called()

@pytest.mark.asyncio
async def test_get_or_create_user_exists_with_change(user_repository: UserRepository, mock_session):
    session_mock, result_mock = mock_session
    # Arrange
    telegram_id = 123
    old_username = "olduser"
    old_first_name = "Old"
    new_username = "newuser"
    new_first_name = "New"
    existing_user = User(id=1, telegram_id=telegram_id, username=old_username, first_name=old_first_name)

    result_mock.scalar_one.return_value = existing_user

    # Act
    user = await user_repository.get_or_create_user(telegram_id, new_username, new_first_name)

    # Assert
    assert user == existing_user
    assert user.username == new_username
    assert user.first_name == new_first_name
    session_mock.execute.assert_called_once()
    session_mock.add.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_user_does_not_exist(user_repository: UserRepository, mock_session):
    session_mock, result_mock = mock_session
    # Arrange
    telegram_id = 456
    username = "newbie"
    first_name = "Fresh"

    result_mock.scalar_one.side_effect = NoResultFound

    # Act
    user = await user_repository.get_or_create_user(telegram_id, username, first_name)

    # Assert
    assert user.telegram_id == telegram_id
    assert user.username == username
    assert user.first_name == first_name
    session_mock.execute.assert_called_once()
    session_mock.add.assert_called_once_with(user)

@pytest.mark.asyncio
async def test_get_user_by_telegram_id_exists(user_repository: UserRepository, mock_session):
    session_mock, result_mock = mock_session
    # Arrange
    telegram_id = 789
    expected_user = User(id=3, telegram_id=telegram_id, username="founduser", first_name="Found")

    result_mock.scalar_one_or_none.return_value = expected_user

    # Act
    user = await user_repository.get_user_by_telegram_id(telegram_id)

    # Assert
    assert user == expected_user
    session_mock.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_by_telegram_id_not_exists(user_repository: UserRepository, mock_session):
    session_mock, result_mock = mock_session
    # Arrange
    telegram_id = 101
    
    result_mock.scalar_one_or_none.return_value = None

    # Act
    user = await user_repository.get_user_by_telegram_id(telegram_id)

    # Assert
    assert user is None
    session_mock.execute.assert_called_once() 