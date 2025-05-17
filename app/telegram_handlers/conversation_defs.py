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

# Callback data prefixes
PROPOSAL_TYPE_CALLBACK = "proposal_type_"
CHANNEL_SELECT_CALLBACK = "channel_select_"

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

# Default values or special inputs
NO_CONTEXT_INPUT = "no_context" 