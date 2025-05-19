# CoordinationBot Commands

This file lists all user-facing commands for CoordinationBot, ordered roughly by criticality for core functionality.

## Core User Commands (v0)

*   `/start`
    *   **Description:** Displays a welcome message and implicitly registers the user with the bot.
    *   **Context:** DM with the bot.

*   `/help`
    *   **Description:** Shows a list of available commands. If a question is provided (e.g., `/help how do I see results?`), it uses an LLM to try and answer based on the command descriptions in this document.
    *   **Context:** DM with the bot.

*   `/privacy`
    *   **Description:** Displays the bot's privacy policy, outlining data storage, usage, and anonymity aspects.
    *   **Context:** DM with the bot.

*   `/ask` or `/ask <question>` or `/ask <proposal_id> <question>`
    *   **Description:** Allows users to ask questions. If a `proposal_id` is provided, the question is specifically about that proposal, and related context is prioritized. If the user only types `ask`, the bot will ask if this is specific to a proposal (and if yes, to use `/proposals open` and `/proposals closed` to see their titles and ids), then the user can choose `/ask <question>` for global questions or `/ask <proposal_id> <question>` for proposal-questions.
    *   **Parameters:**
        *   `<question>`: (Optional) The user's question.
        *   `<proposal_id>` (Optional): The ID of a specific proposal to ask about.
    *   **Context:** DM with the bot.

### Proposals

*   `/propose <Title>; <Description>; [Option1, Option2, ... OR "FREEFORM"]`
    *   **Description:** Initiates the creation of a new proposal (multiple-choice or free-form). The bot will then conversationally ask for the proposal's duration and any initial context.
    *   **Parameters:**
        *   `<Title>`: The title of the proposal.
        *   `<Description>`: A detailed description of the proposal.
        *   `[Option1, Option2, ... OR "FREEFORM"]`: For multiple-choice, a comma-separated list of options. For idea generation, the keyword `FREEFORM`.
    *   **Context:** DM with the bot.

*   `/proposals open`
    *   **Description:** Lists all currently open proposals (both multiple-choice and free-form) with their titles and deadlines.
    *   **Context:** DM with the bot.

*   `/proposals closed`
    *   **Description:** Lists all closed proposals with their titles and final outcomes.
    *   **Context:** DM with the bot.

*   `/edit_proposal` or `/edit_proposal <proposal_id>`
    *   **Description:** Allows the original proposer to edit the title, description, or options of their proposal, but only if no votes or submissions have been cast yet. If the user just says `/edit_proposal`, the bot should ask "which proposal? Use `/my_proposals` to list all, then `/edit_proposal <proposal_id>`.
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the proposal to edit.
    *   **Context:** DM with the bot (proposer only).

*   `/cancel_proposal` or `/cancel_proposal <proposal_id>`
    *   **Description:** Allows the original proposer to cancel their active proposal before its deadline. If the user just says `/cancel_proposal`, the bot should ask "which proposal? Use `/my_proposals` to list all, then `/cancel_proposal <proposal_id>`.
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the proposal to cancel.
    *   **Context:** DM with the bot (proposer only).

### Votes and Submissions

*   `/submit <proposal_id> <Your text submission>`
    *   **Description:** Allows a user to submit their free-form text response to an open idea generation proposal.
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the free-form proposal.
        *   `<Your text submission>`: The user's textual input for the proposal.
    *   **Context:** DM with the bot.
    *   **Note:** The "Submit Your Idea" button on channel messages for free-form proposals will guide the user to a DM where they can click a button to prefill their chat input with `@BotUsername submit <proposal_id> `, to which they then add their submission text. This format is handled by the bot.

*   `/view_results` or `/view_results <proposal_id>`
    *   **Description:** Allows any user to view all anonymized free-form text submissions or breakdown of votes (e.g. "30% A, 70% B") for a specific closed proposal. If the user just says `/view_results`, the bot should ask "for which proposal? use `/proposals open` for open proposals, `/proposals closed` for closed proposals, or `/my_proposals` for your proposals. Then use "/view_results <proposal_id>`.
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the closed proposal.
    *   **Context:** DM with the bot.

### User History

*   `/my_votes`
    *   **Description:** Shows the user a list of proposals they have voted on or submitted to, including their response and the proposal's current status/outcome.
    *   **Context:** DM with the bot.

*   `/my_proposals`
    *   **Description:** Shows the user a list of proposals they have proposed, across all channels.
    *   **Context:** DM with the bot.

*   `/my_docs`
    *   **Description:** Shows the user the list of their docs, which they can manage (edit, delete).
    *   **Context:** DM with the bot.

### Documents

*   `/add_doc` or `/add_doc <proposal_id>`
    *   **Description:** Allows the original proposer to add supplementary context (text, URL, or via chat) to their specific proposal after its initial creation. This context is used by the RAG system for `/ask` queries. If the user just says `/add_doc`, the bot should say "which proposal? use `/my_proposals` to list all then `/add_doc <proposal_id>`".
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the proposal to add context to.
        *   (Context can be provided as text/URL directly, or the bot might initiate a short chat).
    *   **Context:** DM with the bot (proposer only).

*   `/view_docs`
    *   **Description:** Lists all authorized channels the bot is configured to work with. Useful for finding a `channel_id`.
    *   **Context:** DM with the bot.

*   `/view_docs <channel_id>`
    *   **Description:** Lists all proposals (ID, title, status) within a specific channel. Useful for finding a `proposal_id`.
    *   **Parameters:**
        *   `<channel_id>`: The ID of the channel to inspect.
    *   **Context:** DM with the bot.

*   `/view_docs <proposal_id>`
    *   **Description:** Lists all context documents (ID, title) attached to a specific proposal. Useful for finding a `document_id`.
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the proposal to inspect.
    *   **Context:** DM with the bot.

*   `/view_doc <document_id>`
    *   **Description:** Displays the full text content of a specific context document.
    *   **Parameters:**
        *   `<document_id>`: The ID of the document to view.
    *   **Context:** DM with the bot.

*   `/edit_doc` or `/edit_doc <document_id>`
    *   **Description:** Allows the original proposer to edit the content of a specific context document they previously added to one of their proposals. (Bot might initiate a conversation to get new content). If the user just says `/edit_doc`, the bot should say "which doc? use `/my_docs` to list all then use `/edit_doc <document_id>`".
    *   **Parameters:**
        *   `<document_id>`: The ID of the proposal-specific document to edit.
    *   **Context:** DM with the bot (proposer of the associated proposal only).

*   `/delete_doc <document_id>`
    *   **Description:** Allows the original proposer to delete a specific context document they previously added to one of their proposals. If the user just says `/delete_doc`, the bot should say "which doc? use `/my_docs` to list all then use `/delete_doc <document_id>`".
    *   **Parameters:**
        *   `<document_id>`: The ID of the proposal-specific document to delete.
    *   **Context:** DM with the bot (proposer of the associated proposal only).

## Admin Commands (v0)

*   `/add_global_doc <URL or paste text>`
    *   **Description:** Allows an administrator to add general context documents (e.g., existing policies, guidelines) to the bot's global knowledge base for the RAG system.
    *   **Parameters:**
        *   `<URL or paste text>`: The URL of the document or the raw text content.
    *   **Context:** DM with the bot (admin only).

*   `/view_global_docs`
    *   **Description:** Lists all global context documents (ID, title) added by administrators.
    *   **Context:** DM with the bot (admin only).

*   `/edit_global_doc` or `/edit_global_doc <document_id>`
    *   **Description:** Allows an administrator to edit the content of a specific global context document. (Bot might initiate a conversation to get new content). If the admin just says `/edit_global_doc`, the bot should ask "which doc? use `/my_docs` to list all then use `/edit_global_doc <document_id>`".
    *   **Parameters:**
        *   `<document_id>`: The ID of the global document to edit.
    *   **Context:** DM with the bot (admin only).

*   `/delete_global_doc` or `/delete_global_doc <document_id>`
    *   **Description:** Allows an administrator to delete a specific global context document from the knowledge base. If the admin just says `/delete_global_doc`, the bot should ask "which doc? use `/my_docs` to list all then use `/delete_global_doc <document_id>`".
    *   **Parameters:**
        *   `<document_id>`: The ID of the global document to delete.
    *   **Context:** DM with the bot (admin only).