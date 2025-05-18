import re # For escaping markdown
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from app.persistence.models.proposal_model import Proposal, ProposalType
from app.persistence.models.user_model import User # For proposer info
from datetime import datetime
from telegram.ext import CallbackContext
from typing import List, Dict, Any, Optional, Union

MAX_MESSAGE_LENGTH = 4096 # Telegram's max message length

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
    # Proposer name might come from Telegram, usually safe, but good to be cautious if ever user-settable
    proposer_name = escape_markdown_v2(proposer.first_name or proposer.username or f"User {proposer.telegram_id}")
    
    # Dates formatted by strftime with '-' or '.' should also be escaped if they are part of the text argument of send_message.
    # Here, deadline_str is interpolated into an f-string which is then sent.
    deadline_str = escape_markdown_v2(proposal.deadline_date.strftime("%Y-%m-%d %H:%M UTC"))

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

def get_free_form_submit_button(proposal_id: int) -> InlineKeyboardMarkup:
    """Returns an inline keyboard with a 'Submit Your Idea' button for free-form proposals."""
    button_text = "💬 Submit Your Idea"
    # switch_inline_query_current_chat will prefill the user's input field with the query
    # when they are in a DM with the bot.
    query_to_prefill = f"/submit {proposal_id} " 
    keyboard = [[InlineKeyboardButton(button_text, switch_inline_query_current_chat=query_to_prefill)]]
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