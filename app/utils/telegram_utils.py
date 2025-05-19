import re # For escaping markdown
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from app.persistence.models.proposal_model import Proposal, ProposalType
from app.persistence.models.user_model import User # For proposer info
from datetime import datetime, timezone
from dateutil import tz # Added for timezone conversion
from telegram.ext import CallbackContext
from typing import List, Dict, Any, Optional, Union

MAX_MESSAGE_LENGTH = 4096 # Telegram's max message length

# Define the target timezone (PST)
PST = tz.gettz('America/Los_Angeles')

def escape_markdown_v2(text: str) -> str:
    """Helper function to escape text for MarkdownV2."""
    # Characters to escape for MarkdownV2
    # Order matters for some (e.g., escape `\` before other characters that might use it)
    # However, simple replacement should be fine for this set.
    escape_chars = r'_[]()~`>#+-=|{}.!'
    # Precede each character in the set with a backslash
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def format_proposal_message(proposal: Proposal, proposer: User) -> str:
    """Formats a proposal message for posting to the channel."""
    # Escape all user-provided and potentially problematic parts
    escaped_title = escape_markdown_v2(proposal.title)
    escaped_description = escape_markdown_v2(proposal.description)
    
    # Determine proposer display name: @username, then first_name, then User ID
    if proposer.username:
        proposer_display_name = f"@{proposer.username}"
    elif proposer.first_name:
        proposer_display_name = proposer.first_name
    else:
        proposer_display_name = f"User {proposer.telegram_id}"
    
    proposer_name = escape_markdown_v2(proposer_display_name)
    
    # Dates formatted by strftime with '-' or '.' should also be escaped if they are part of the text argument of send_message.
    # Here, deadline_str is interpolated into an f-string which is then sent.
    # Convert deadline_date (assumed to be UTC) to PST for display
    # deadline_pst = proposal.deadline_date.astimezone(PST) if proposal.deadline_date.tzinfo else proposal.deadline_date.replace(tzinfo=timezone.utc).astimezone(PST)
    # deadline_str = escape_markdown_v2(deadline_pst.strftime("%Y-%m-%d %H:%M %Z")) # Display with timezone
    deadline_str = escape_markdown_v2(format_datetime_for_display(proposal.deadline_date)) # Use the new helper

    message_text = f"📢 **New {'Proposal' if proposal.proposal_type == ProposalType.MULTIPLE_CHOICE.value else 'Idea Collection'}: {escaped_title}**\n\n"
    message_text += f"Proposed by: {proposer_name}\n\n"
    message_text += f"_{escaped_description}_\n\n"

    if proposal.proposal_type == ProposalType.MULTIPLE_CHOICE.value:
        if proposal.options:
            message_text += "Options:\n"
            for i, option_text in enumerate(proposal.options):
                # Escape each option text
                escaped_option_text = escape_markdown_v2(option_text)
                message_text += f"{i+1}️⃣ {escaped_option_text}\n"
        # Inline keyboard for voting will be added by the caller using reply_markup.
        message_text += f"\nVoting ends: {deadline_str}\n"

    elif proposal.proposal_type == ProposalType.FREE_FORM.value:
        # Note: The command `/submit {proposal.id} Your idea here` is wrapped in backticks, so it's pre-formatted code.
        # The proposal.id itself if it were part of a normal string would need escaping.
        # Since it's inside backticks for a code block, it's generally fine.
        # However, the surrounding text if not part of code blocks should be escaped.
        static_text_part = "This is a free-form submission. To submit your idea, DM the bot with:"
        message_text += escape_markdown_v2(static_text_part) + "\n"
        message_text += f"`/submit {proposal.id} Your idea here`\n"
        # Escape the line with parentheses
        proposal_id_line = f"(Proposal ID: {proposal.id})"
        message_text += escape_markdown_v2(proposal_id_line) + "\n\n"
        message_text += f"Submissions end: {deadline_str}"
    
    return message_text

def format_datetime_for_display(dt: datetime, target_tz_str: str = 'America/Los_Angeles') -> str:
    """Formats a datetime object to a string for display in a target timezone."""
    if not dt:
        return "Not set"
    
    target_tz = tz.gettz(target_tz_str)
    if not target_tz:
        # Fallback or error if timezone string is invalid
        return dt.strftime("%Y-%m-%d %H:%M UTC") # Default to UTC display

    # Ensure the datetime is timezone-aware (assume UTC if naive)
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt_aware = dt.replace(tzinfo=timezone.utc)
    else:
        dt_aware = dt
    
    dt_localized = dt_aware.astimezone(target_tz)
    return dt_localized.strftime("%Y-%m-%d %H:%M %Z") # e.g., "2024-05-17 10:30 PST"

def get_free_form_submit_button(proposal_id: int, bot_username: str) -> InlineKeyboardMarkup:
    """Returns an inline keyboard with a 'Submit Your Idea' button that opens a DM to the bot."""
    button_text = "💬 Submit Your Idea"
    # Construct the deep-linking URL
    # Example: https://t.me/YourBotUsername?start=submit_123
    # Ensure bot_username does not have '@' if context.bot.username provides it like that.
    # The URL typically uses the username without '@'.
    cleaned_bot_username = bot_username.lstrip('@')
    url = f"https://t.me/{cleaned_bot_username}?start=submit_{proposal_id}"
    
    keyboard = [[InlineKeyboardButton(button_text, url=url)]]
    return InlineKeyboardMarkup(keyboard)

def create_proposal_options_keyboard(proposal_id: int, options: List[str]) -> InlineKeyboardMarkup:
    """
    Creates an inline keyboard with buttons for each proposal option.
    Callback data format: vote_[proposal_id]_[option_index]
    """
    keyboard = []
    for index, option_text in enumerate(options):
        callback_data = f"vote_{proposal_id}_{index}"
        # Ensure option_text for button isn't too long for Telegram (64 bytes for button text)
        # A simple truncation, could be smarter if needed.
        button_text = option_text[:60] # Max 64 bytes, play safe with characters
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    return InlineKeyboardMarkup(keyboard)

async def send_message_in_chunks(context: CallbackContext, chat_id: int, text: str, **kwargs) -> None:
    """Sends a message, splitting it into chunks if it exceeds Telegram's max length."""
    if not text:
        return
    
    max_len = MAX_MESSAGE_LENGTH

    for i in range(0, len(text), max_len):
        chunk = text[i:i + max_len]
        await context.bot.send_message(chat_id=chat_id, text=chunk, **kwargs)

def create_telegram_message_link(target_channel_id: Union[str, int], message_id: int) -> Optional[str]:
    """
    Creates a direct t.me link to a message in a channel or supergroup.

    Args:
        target_channel_id: The ID of the channel/supergroup (e.g., -1001234567890 or "@publicchannel").
        message_id: The ID of the message.

    Returns:
        A string URL if a link can be formed, otherwise None.
    """
    if not target_channel_id or not message_id:
        return None

    tc_id_str = str(target_channel_id)

    if tc_id_str.startswith("-100"):  # Private supergroup/channel
        numeric_id_part = tc_id_str[4:]
        return f"https://t.me/c/{numeric_id_part}/{message_id}"
    elif tc_id_str.startswith("@"):  # Public channel with @username
        username_part = tc_id_str[1:]  # Remove "@"
        return f"https://t.me/{username_part}/{message_id}"
    # Optional: Handle public channel username without '@' if it's a possible format
    # elif not tc_id_str.startswith("-") and not tc_id_str.isdigit(): 
    #     return f"https://t.me/{tc_id_str}/{message_id}"
    
    return None 