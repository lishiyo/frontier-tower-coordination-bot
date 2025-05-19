# Conversation states for the proposal creation flow
(
    COLLECT_TITLE,
    COLLECT_DESCRIPTION,
    COLLECT_OPTIONS_TYPE,
    COLLECT_PROPOSAL_TYPE,  # Explicitly ask for proposal type (multiple_choice or free_form)
    COLLECT_OPTIONS,        # Specifically for collecting options if multiple_choice
    ASK_CHANNEL,            # For selecting the target channel (if multi-channel is active)
    ASK_DURATION,
    ASK_CONTEXT,
    CONFIRM_PROPOSAL,       # Optional: A final confirmation step before submitting
) = range(9)

# States for /edit_proposal (if needed, or manage via context + simple handlers)
# EDIT_PROPOSAL_NEW_TITLE, EDIT_PROPOSAL_NEW_DESCRIPTION, EDIT_PROPOSAL_NEW_OPTIONS = range(8, 11) # Old, overlapping

# New states for /edit_proposal ConversationHandler
(
    SELECT_EDIT_ACTION,     # Ask user what they want to edit (Title, Description, Options, All)
    EDIT_TITLE,             # Collect new title
    EDIT_DESCRIPTION,       # Collect new description
    EDIT_OPTIONS,           # Collect new options (if MC proposal)
    CONFIRM_EDIT_PROPOSAL   # Show changes and ask for confirmation
) = range(13, 18) # Start from 13 to avoid conflict

# States for /add_global_doc
ADD_GLOBAL_DOC_CONTENT, ADD_GLOBAL_DOC_TITLE = range(11, 13)

# Callback data prefixes
PROPOSAL_TYPE_CALLBACK = "proposal_type_"
CHANNEL_SELECT_CALLBACK = "channel_select_"
VOTE_CALLBACK_PREFIX = "vote_" # For actual votes

# New callback data for /proposals filter
PROPOSAL_FILTER_CALLBACK_PREFIX = "proposal_filter_"
PROPOSAL_FILTER_OPEN = f"{PROPOSAL_FILTER_CALLBACK_PREFIX}open"
PROPOSAL_FILTER_CLOSED = f"{PROPOSAL_FILTER_CALLBACK_PREFIX}closed"

# User data keys
USER_DATA_PROPOSAL_TITLE = "proposal_title"
USER_DATA_PROPOSAL_DESCRIPTION = "proposal_description"
USER_DATA_PROPOSAL_TYPE = "proposal_type"
USER_DATA_PROPOSAL_OPTIONS = "proposal_options"
USER_DATA_TARGET_CHANNEL_ID = "target_channel_id"
USER_DATA_DEADLINE_DATE = "deadline_date"
USER_DATA_CONTEXT_DOCUMENT_ID = "context_document_id"
USER_DATA_PROPOSAL_PARTS = "proposal_parts" # For initial parsing
USER_DATA_CURRENT_CONTEXT = "current_context" # For storing context during conversation
USER_DATA_EDIT_PROPOSAL_ID = "edit_proposal_id"
USER_DATA_EDIT_PROPOSAL_ORIGINAL = "edit_proposal_original" # Store original proposal for reference
USER_DATA_EDIT_CHANGES = "edit_proposal_changes" # dict to store {title: new_val, desc: new_val, opts: new_val}

# Default values or special inputs
NO_CONTEXT_INPUT = "no_context" 