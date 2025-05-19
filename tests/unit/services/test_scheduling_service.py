import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application
import logging # Added for caplog.set_level

from app.services import scheduling_service # Import the module to patch its globals
from app.services.scheduling_service import (
    start_scheduler_async,
    stop_scheduler,
    check_proposal_deadlines_job,
    add_deadline_check_job 
)
from app.core.proposal_service import ProposalService # For mocking

@pytest.fixture
def mock_apscheduler():
    # Patch the global scheduler instance within the scheduling_service module
    with patch('app.services.scheduling_service.scheduler', spec=AsyncIOScheduler) as mock_sched:
        yield mock_sched

@pytest.fixture
def mock_bot_app():
    return AsyncMock(spec=Application)

@pytest.fixture
def mock_async_session_local():
    # This mock represents the async context manager returned by AsyncSessionLocal()
    mock_session_instance = AsyncMock()
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_session_instance
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)
    
    # Patch AsyncSessionLocal where it's used in check_proposal_deadlines_job
    with patch('app.services.scheduling_service.AsyncSessionLocal', return_value=mock_context_manager) as mock_asl:
        yield {
            'mock_async_session_local': mock_asl, 
            'mock_session_instance': mock_session_instance,
            'mock_context_manager': mock_context_manager
        }

@pytest.fixture
def mock_proposal_service():
    with patch('app.services.scheduling_service.ProposalService', autospec=True) as MockPS:
        mock_instance = MockPS.return_value
        mock_instance.process_expired_proposals = AsyncMock()
        yield mock_instance

# --- Test start_scheduler_async ---
@pytest.mark.asyncio
async def test_start_scheduler_async_not_running(mock_apscheduler, mock_bot_app):
    mock_apscheduler.running = False
    with patch('app.services.scheduling_service.add_deadline_check_job') as mock_add_job:
        await start_scheduler_async(mock_bot_app)
        assert scheduling_service._bot_app is mock_bot_app
        mock_add_job.assert_called_once()
        mock_apscheduler.start.assert_called_once()

@pytest.mark.asyncio
async def test_start_scheduler_async_already_running(mock_apscheduler, mock_bot_app, caplog):
    caplog.set_level(logging.INFO) # Ensure INFO logs are captured
    mock_apscheduler.running = True
    await start_scheduler_async(mock_bot_app)
    assert scheduling_service._bot_app is mock_bot_app # _bot_app should still be set
    mock_apscheduler.start.assert_not_called()
    assert "APScheduler is already running." in caplog.text

@pytest.mark.asyncio
async def test_start_scheduler_async_start_error(mock_apscheduler, mock_bot_app, caplog):
    caplog.set_level(logging.ERROR) # Ensure ERROR logs are captured (or INFO if it logs at INFO then ERROR)
    mock_apscheduler.running = False
    mock_apscheduler.start.side_effect = Exception("Scheduler Start Error")
    with patch('app.services.scheduling_service.add_deadline_check_job'), pytest.raises(Exception, match="Scheduler Start Error"):
        await start_scheduler_async(mock_bot_app)
    assert "Error starting APScheduler" in caplog.text

# --- Test stop_scheduler ---
def test_stop_scheduler_running(mock_apscheduler):
    mock_apscheduler.running = True
    stop_scheduler()
    mock_apscheduler.shutdown.assert_called_once()

def test_stop_scheduler_not_running(mock_apscheduler, caplog):
    mock_apscheduler.running = False
    stop_scheduler()
    mock_apscheduler.shutdown.assert_not_called()
    # No specific log for this case in current code, but good to check no error

def test_stop_scheduler_shutdown_error(mock_apscheduler, caplog):
    caplog.set_level(logging.ERROR)
    mock_apscheduler.running = True
    mock_apscheduler.shutdown.side_effect = Exception("Scheduler Shutdown Error")
    # Should not raise, but log
    stop_scheduler()
    assert "Error stopping APScheduler" in caplog.text

# --- Test check_proposal_deadlines_job ---
@pytest.mark.asyncio
async def test_check_deadlines_bot_app_none(caplog):
    caplog.set_level(logging.ERROR) # This logs an error
    scheduling_service._bot_app = None # Ensure it's None for this test
    await check_proposal_deadlines_job()
    assert "Bot application instance not available" in caplog.text

@pytest.mark.asyncio
async def test_check_deadlines_success_proposals_processed(
    mock_async_session_local, mock_proposal_service, mock_bot_app, caplog
):
    caplog.set_level(logging.INFO)
    scheduling_service._bot_app = mock_bot_app # Set the global bot_app
    mock_proposal_service.process_expired_proposals.return_value = [MagicMock(), MagicMock()] # Two proposals
    
    await check_proposal_deadlines_job()
    
    mock_async_session_local['mock_async_session_local'].assert_called_once()
    mock_proposal_service.process_expired_proposals.assert_called_once()
    assert "Deadline check job processed 2 proposals." in caplog.text
    # Verify ProposalService was instantiated correctly within the job
    # This requires accessing the constructor mock if ProposalService was patched via its module path
    # In our fixture, mock_proposal_service *is* the instance, so we check its method calls.

@pytest.mark.asyncio
async def test_check_deadlines_success_no_proposals(
    mock_async_session_local, mock_proposal_service, mock_bot_app, caplog
):
    caplog.set_level(logging.INFO)
    scheduling_service._bot_app = mock_bot_app
    mock_proposal_service.process_expired_proposals.return_value = [] # No proposals
    
    await check_proposal_deadlines_job()
    assert "Deadline check job found no proposals to process" in caplog.text

@pytest.mark.asyncio
async def test_check_deadlines_service_exception(
    mock_async_session_local, mock_proposal_service, mock_bot_app, caplog
):
    caplog.set_level(logging.ERROR)
    scheduling_service._bot_app = mock_bot_app
    mock_proposal_service.process_expired_proposals.side_effect = Exception("Service Error")
    
    await check_proposal_deadlines_job()
    assert "Error in check_proposal_deadlines_job: Service Error" in caplog.text

# --- Test add_deadline_check_job ---
def test_add_deadline_check_job_success(mock_apscheduler, caplog):
    caplog.set_level(logging.INFO)
    add_deadline_check_job()
    mock_apscheduler.add_job.assert_called_once_with(
        check_proposal_deadlines_job,
        'interval',
        minutes=1,
        id="deadline_check_job",
        replace_existing=True
    )
    assert "Job 'deadline_check_job' added to scheduler" in caplog.text

def test_add_deadline_check_job_error(mock_apscheduler, caplog):
    caplog.set_level(logging.ERROR)
    mock_apscheduler.add_job.side_effect = Exception("Add Job Error")
    add_deadline_check_job()
    assert "Error adding deadline_check_job to scheduler" in caplog.text 