# CoordinationBot Commands

This file lists all user-facing commands for CoordinationBot, ordered roughly by criticality for core functionality.

## Core User Commands (v0)

*   `/start`
    *   **Description:** Displays a welcome message and implicitly registers the user with the bot.
    *   **Context:** DM with the bot.

*   `/help`
    *   **Description:** Shows a list of available commands, their usage, and a brief explanation of the bot's purpose.
    *   **Context:** DM with the bot.

*   `/propose <Title>; <Description>; [Option1, Option2, ... OR "FREEFORM"]`
    *   **Description:** Initiates the creation of a new proposal (multiple-choice or free-form). The bot will then conversationally ask for the proposal's duration and any initial context.
    *   **Parameters:**
        *   `<Title>`: The title of the proposal.
        *   `<Description>`: A detailed description of the proposal.
        *   `[Option1, Option2, ... OR "FREEFORM"]`: For multiple-choice, a comma-separated list of options. For idea generation, the keyword `FREEFORM`.
    *   **Context:** DM with the bot.

*   `/submit <proposal_id> <Your text submission>`
    *   **Description:** Allows a user to submit their free-form text response to an open idea generation proposal.
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the free-form proposal.
        *   `<Your text submission>`: The user's textual input for the proposal.
    *   **Context:** DM with the bot.

*   `/ask <question>` or `/ask <proposal_id> <question>`
    *   **Description:** Allows users to ask questions. If a `proposal_id` is provided, the question is specifically about that proposal, and related context is prioritized.
    *   **Parameters:**
        *   `<question>`: The user's question.
        *   `<proposal_id>` (Optional): The ID of a specific proposal to ask about.
    *   **Context:** DM with the bot.

*   `/my_votes`
    *   **Description:** Shows the user a list of proposals they have voted on or submitted to, including their response and the proposal's current status/outcome.
    *   **Context:** DM with the bot.

*   `/my_proposals`
    *   **Description:** Shows the user a list of proposals they have proposed, across all channels.
    *   **Context:** DM with the bot.

*   `/proposals open`
    *   **Description:** Lists all currently open proposals (both multiple-choice and free-form) with their titles and deadlines.
    *   **Context:** DM with the bot.

*   `/proposals closed`
    *   **Description:** Lists all closed proposals with their titles and final outcomes.
    *   **Context:** DM with the bot.

*   `/edit_proposal <proposal_id>`
    *   **Description:** Allows the original proposer to edit the title, description, or options of their proposal, but only if no votes or submissions have been cast yet.
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the proposal to edit.
    *   **Context:** DM with the bot (proposer only).

*   `/cancel_proposal <proposal_id>`
    *   **Description:** Allows the original proposer to cancel their active proposal before its deadline.
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the proposal to cancel.
    *   **Context:** DM with the bot (proposer only).

*   `/add_proposal_context <proposal_id>`
    *   **Description:** Allows the original proposer to add supplementary context (text, URL, or via chat) to their specific proposal after its initial creation. This context is used by the RAG system for `/ask` queries.
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the proposal to add context to.
        *   (Context can be provided as text/URL directly, or the bot might initiate a short chat).
    *   **Context:** DM with the bot (proposer only).

*   `/view_submissions <proposal_id>`
    *   **Description:** Allows any user to view all anonymized free-form text submissions for a specific closed idea generation proposal.
    *   **Parameters:**
        *   `<proposal_id>`: The ID of the closed free-form proposal.
    *   **Context:** DM with the bot.

*   `/privacy`
    *   **Description:** Displays the bot's privacy policy, outlining data storage, usage, and anonymity aspects.
    *   **Context:** DM with the bot.

## Admin Commands (v0)

*   `/add_doc <URL or paste text>`
    *   **Description:** Allows an administrator to add general context documents (e.g., existing policies, guidelines) to the bot's knowledge base for the RAG system.
    *   **Parameters:**
        *   `<URL or paste text>`: The URL of the document or the raw text content.
    *   **Context:** DM with the bot (admin only).