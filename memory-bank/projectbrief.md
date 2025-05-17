# PRD: CoordinationBot (v0)

We are building a Telegram bot called `CoordinationBot` for policy proposals and voting at Frontier Tower, with RAG for context and future personalized recommendations.

This document outlines the product requirements for `CoordinationBot`, which is designed to facilitate policy proposals, idea generation, voting, and information dissemination within the community. The bot will allow members to create proposals, vote on predefined options or submit free-form responses, access contextual information about policies, and (in the future) receive personalized voting recommendations.

**Core features (v0):**
- you can DM the bot to create policy proposals like "what kind of events should we do" and then it will post your proposal in a channel and people can vote on it
- it will store everyone's voting history, the proposals, the proposals outcomes and so on
- the answers can be free-form, it's not always select a single option (for example for "what kind of events should we do", that's fill-in)
- The votes should be anonymous, you can't see other people's votes until the deadline has passed and results are published.
- You should be able to DM the bot for more info on what the policy is about. Proposers can add detailed context (documents/chat with bot) specific to their proposals, which the bot will use. The bot can also DM the original proposal poster with questions if general context is insufficient.
    - the original proposal poster can also ask the bot to post in the full public channel about an update, in order to clarify a question for everyone
- in the future (v1) it should also be plugged into more context specific to you (chats with you, your own docs etc) beyond just your voting history, so it could recommend you how to vote as well

**(Enhanced) Multi-Channel Proposal Destination (v0.5 / v1):**
- The bot can be configured to post proposals to a single designated channel (current v0 behavior via `TARGET_CHANNEL_ID`).
- Future Enhancement: The bot can be configured to operate with multiple authorized channels. Users can then initiate proposals directly within an authorized channel (with follow-up in DM), or when proposing via DM, they can select the target channel from a list of authorized channels.


**User Stories**

*   **As a Proposer, I want to:**
    *   Create a new policy proposal with a title, description, and a set of predefined voting options or a free-form option. The bot will then ask me for the voting deadline (which I can specify as a duration or an end date/time), so that the community can vote on it. (Note: This will use the default channel or trigger channel selection if multi-channel is active).
    *   Create a new idea generation proposal with a title and description, asking for free-form text input from members. The bot will ask me for the submission deadline (which I can specify as a duration or an end date/time), so I can gather diverse ideas. (Note: This will use the default channel or trigger channel selection if multi-channel is active).
    *   **(New)** Type `/propose` in my project's specific Telegram channel, and have the bot guide me through adding details (like duration and context) via DM, then automatically post the formatted proposal back to that same project channel.
    *   **(New)** When I DM the bot with `/propose`, if the bot is configured to work with multiple community channels, I want to be asked and be able to select which channel my proposal is for.
    *   Be notified when my proposal is created and when its deadline passes and results are published.
    *   Be able to add more context about my proposal to the bot using `/add_doc <proposal_id>` (e.g., by uploading a document or chatting with the bot about it), so users asking about my proposal can get more detailed information.
    *   Be able to edit the title, description, or options of my proposal if no votes have been cast yet.
    *   Be able to cancel my active proposals before their deadline.
    *   Be able to edit a document I previously added to my proposal using `/edit_doc <document_id>`.
    *   Be able to delete a document I previously added to my proposal using `/delete_doc <document_id>`.
*   **As a Voter/Submitter, I want to:**
    *   Be notified in a central channel when a new proposal is available.
    *   Easily vote on a multiple-choice proposal using inline buttons in Telegram.
    *   Easily submit my free-form text response to an idea generation proposal by DMing the bot.
    *   Be assured my individual vote/submission is anonymous until the deadline passes.
    *   Be able to change my vote/submission before the deadline.
    *   View a history of proposals I've voted on or submitted to.
    *   Be notified of the outcome of proposals.
*   **As a Community Member, I want to:**
    *   View all open proposals and their deadlines.
    *   View all closed proposals and their outcomes (including aggregated vote counts for multiple-choice or a list/summary of free-form submissions via `/view_results <proposal_id>`).
    *   DM the bot to ask questions about existing policies or context documents and receive relevant answers.
*   **As an Admin/Moderator, I want to:**
    *   Upload general context documents using `/add_global_doc <URL or paste text>`, view them with `/view_global_docs`, edit them with `/edit_global_doc <document_id>`, and delete them with `/delete_global_doc <document_id>`, so the bot can use these for answering questions.
    *   Invite the bot to channels.
    *   View all proposals, their outcomes, and (after results are published) who submitted/voted for transparency and record-keeping (for v0).
    *   **(New)** Configure the bot with one or more 'authorized proposal channel IDs' where proposals can be initiated or targeted.
    *   (Future v1) Cancel or moderate any proposals, edit proposals, extend deadlines, close proposals early, or ban users.
*   **As a Future User (with consent), I want to:**
    *   Receive personalized recommendations on how to vote based on my past voting history and other relevant personal context (my documents, chats with the bot).

**5. Functional Requirements**

**5.1. Core Bot Interaction & User Management**
    *   **FR1.1:** Bot accessible via Telegram DM and posts to a designated Telegram Channel (or multiple, if configured).
    *   **FR1.2:** Implicit user registration: store `telegram_id`, `first_name`, `username` (if available) on first interaction.
    *   **FR1.3:** `/start` command: Welcome message.
    *   **FR1.4:** `/help` command: Display available commands and usage (including `/privacy`).
    *   **FR1.5:** `/privacy` command (DM): Displays the bot's privacy policy, outlining data storage, usage, and anonymity aspects.

**5.2. Proposal Creation**
    *   **FR2.1 (Proposing - Flexible Input):**
        *   User DMs bot with `/propose [Initial Information]` or types in an authorized channel: `/propose [Initial Information]`.
        *   `[Initial Information]` can be:
            *   Empty (just `/propose`).
            *   Only a title (e.g., `/propose My Proposal Title`).
            *   A fully structured command (e.g., `/propose Title; Description; Option1, Option2` or `/propose Title; Description; FREEFORM`).
        *   The bot will initiate a `ConversationHandler` flow.
        *   **If core details (title, description, options/type) are missing from `[Initial Information]`, the bot will sequentially ask for them.**
            *   Example interaction if user sends just `/propose`:
                *   Bot: "Okay, let's create a new proposal! What would you like to name it?"
                *   User: "Community Event Ideas"
                *   Bot: "Got it. Can you provide a brief description for 'Community Event Ideas'?"
                *   User: "Let's brainstorm some fun events for next quarter."
                *   Bot: "Thanks! Is this a 'multiple_choice' proposal (where you'll list options for people to vote on) or a 'free_form' idea collection? If multiple choice, please list the options separated by commas. Otherwise, just say 'freeform'."
                *   User: "freeform"
        *   Once core details are collected conversationally or parsed from a structured command, the flow proceeds to channel determination (if applicable), duration, and initial context. 

        *   **Proposal Initiation Source & Channel Targeting (remains largely the same, triggered after core details are known):**
            *   **FR2.1.A (DM Initiation - Single Channel Mode):** If a user DMs the bot and core details are gathered, and the bot is configured with a single default target channel, this channel is used. The bot proceeds to ask for duration.
            *   **FR2.1.B (DM Initiation - Multi-Channel Mode):** If a user DMs the bot, core details are gathered, and the bot is configured for multiple authorized proposal channels:
                *   The bot will ask the user (e.g., after parsing the initial title/desc/options): 'Which channel is this proposal for?'
                *   The bot will present a list of authorized channels (e.g., via inline keyboard in the DM).
                *   The user's selection will determine the `target_channel_id` for the proposal.
                *   The rest of the proposal creation flow (duration, context) continues in DM."
            *   **FR2.1.C (In-Channel Initiation):** "If a user types `/propose...` directly within a Telegram channel where the bot is a member:
                *   The bot checks if this channel is an 'authorized proposal channel' (see FR5.9).
                *   If authorized:
                    *   The bot uses this channel's ID as the `target_channel_id`.
                    *   The bot sends a DM to the proposing user to continue the setup, (e.g., 'Let\'s continue setting up your proposal \'{Title}\u0027 for the \'{Channel Name}\u0027 channel. How long should it be open for...?'). The bot might need to prompt the user to DM it first if it can't initiate DMs (e.g., user has privacy settings or hasn't started a chat with the bot).
                    *   The final proposal is posted back to the originating authorized channel.
                *   If not an authorized channel for proposals, or if the bot cannot DM the user, the bot may post an ephemeral clarifying message in the channel if possible (e.g. 'Please DM me to create proposals, or use an authorized channel.'), or simply not respond to the in-channel `/propose`. Behavior might depend on bot's permissions in that channel."

        *   **(Common Flow after channel is determined):**
            *   Bot will then ask: "How long should this proposal be open for voting/submissions, or until when would you like to set the deadline?"
            *   User provides a natural language response (e.g., "7 days", "until May 21st at 5 PM", "for 3 weeks").
            *   The bot will use an LLM to parse this response and determine the `deadline_date`. Bot confirms interpretation with user if ambiguous.
            *   **Bot then asks:** "Great! Your proposal details are set. Do you have any extra context or background information to add? This won't appear in the public poll itself but will be very helpful if users ask questions about the proposal. You can paste text, provide a URL, or just say 'no' for now."
            *   User responds. If context (text/URL) is provided, bot processes and stores it (see FR2.5 logic), associating it with the new proposal.
    *   **FR2.2 (Internal Parsing & Validation):** Bot internally parses and validates all collected/provided information (title, description, options, type, deadline, channel). Confirms deadline interpretation with user if ambiguous.
    *   **FR2.3 (Storage):** Store proposal details in the database, including `proposal_type` ("multiple_choice" or "free_form"), proposer, creation date, LLM-parsed `deadline_date`, and the **`target_channel_id`**. For multiple-choice, `options` are stored as a list of strings.
    *   **FR2.4 (Confirmation DM):** Bot sends confirmation DM to proposer: "Understood. Your proposal ID is `[proposal_id]`. It will be posted to the channel '[Channel Name/ID]' shortly. If you think of more context to add later, you can always DM me: `/add_doc <proposal_id> <URL or paste text>`." (Channel name/ID included for clarity in multi-channel scenarios).
    *   **FR2.5 (Adding Context - Proposer - Later or if initial offer declined):** `/add_doc <proposal_id> <URL or paste text OR trigger chat>` (DM)
        *   Allows proposer to upload a document, paste text, or engage in a short chat with the bot to add context to their specific proposal *after* initial creation or if they initially declined to add context.
        *   This content is processed (chunked, embedded) and stored, linked to the `proposal_id` in the `Document` table, for use in RAG when users ask about this proposal. If text is from chat, `source_url` in `Document` table might indicate "proposer_chat_context". The full text content is also stored directly for later viewing.

**5.2.B Document Management (Proposer-Specific)**
    *   **FR2.6 (Editing Proposal Document - Proposer):** `/edit_doc <document_id>` (DM)
        *   Allows the original proposer to edit the content of a specific context document they previously added to one of their proposals.
        *   Bot verifies the user is the proposer of the proposal linked to the `document_id`.
        *   Bot may initiate a conversation to get the new content for the document.
        *   Updates the `raw_content` in the `Document` table and re-processes for vector DB if necessary.
    *   **FR2.7 (Deleting Proposal Document - Proposer):** `/delete_doc <document_id>` (DM)
        *   Allows the original proposer to delete a specific context document they previously added to one of their proposals.
        *   Bot verifies the user is the proposer of the proposal linked to the `document_id`.
        *   Removes the document record from the `Document` table and associated chunks from the vector DB.

**5.3. Proposal Broadcasting & Interaction**
    *   **FR3.1:** Bot posts new proposal to the proposal's designated **`target_channel_id`** (as stored in the proposal record).
        *   **Multiple Choice:** Message includes title, description, proposer, deadline, and inline keyboard buttons for each voting option. Callback data for buttons includes `proposal_id` and `option_index` (0-based index of the option).
        *   **Free Form:** Message includes title, description, proposer, deadline, and clear instructions on how to submit via DM (e.g., "DM me `/submit <proposal_id> Your idea here`"). Proposal ID should be clearly visible. Includes an inline button "💬 Submit Your Idea" using `switch_inline_query_current_chat` to prefill the `/submit <proposal_id> ` command in the user's DM with the bot.
    *   **FR3.2:** Store `channel_message_id` (of the message in the `target_channel_id`) for future updates (e.g., posting results).

**5.4. Voting & Submission**
    *   **FR4.1 (Multiple Choice Voting):**
        *   User clicks inline button in the channel.
        *   Bot receives `CallbackQuery`, extracts `proposal_id` and `option_index`.
        *   Bot records vote (user, proposal, the *selected option string* corresponding to the `option_index`) in the `Submission` table as `response_content`.
        *   Vote is anonymous (no public acknowledgment of who voted for what until results).
        *   User receives ephemeral confirmation ("Vote recorded").
        *   User can change their vote by clicking another option before the deadline; the previous vote is updated.
    *   **FR4.2 (Free Form Submission):**
        *   User DMs the bot: `/submit <proposal_id> <Their free-form text response>`
        *   Bot validates `proposal_id` (exists, is free-form, is open).
        *   Bot records submission (user, proposal, text) in the `Submission` table.
        *   Submission is anonymous.
        *   User receives DM confirmation ("Submission recorded").
        *   User can resubmit before the deadline; the previous submission is updated.
    *   **FR4.3:** Only one vote/submission per user per proposal.
    *   **FR4.4 (Proposal Editing - Proposer):** `/edit_proposal <proposal_id>` (DM)
        *   Allows proposer to edit `title`, `description`, and `options` (if multiple-choice) of their own proposal.
        *   Condition: Only allowed if no votes/submissions have been made for the proposal yet.
        *   If edited, bot updates the proposal message in the `target_channel_id`.
    *   **FR4.5 (Proposal Cancellation - Proposer):** `/cancel_proposal <proposal_id>` (DM)
        *   Allows proposer to cancel their own proposal if its `status` is "open".
        *   Bot updates proposal `status` to "cancelled", updates the channel message (e.g., "This proposal has been cancelled by the proposer.") in the `target_channel_id`, and notifies any existing voters/submitters via DM (optional).

**5.5. Deadline Management & Results**
    *   **FR5.1:** Automated scheduler checks for proposals past their deadline.
    *   **FR5.2:** For each expired proposal:
        *   Set proposal `status` to "closed".
        *   **Multiple Choice:** Tally votes from `Submission` table. Determine outcome. If there's a tie, the outcome reflects the tie (e.g., "Tie between Option A and Option B"). Store outcome and vote counts in `Proposal` table.
        *   **Free Form:** Retrieve all `response_content`. Use an LLM to cluster submissions and generate a summary of the main themes/clusters. Store this summary as `Proposal.outcome` and the full list of anonymized submissions in `Proposal.raw_results`.
    *   **FR5.3:** Bot posts results to the proposal's `target_channel_id` (e.g., edits original message or replies to it).
        *   **Multiple Choice:** Display winning option(s) (or tie details) and vote counts/percentages for all options.
        *   **Free Form:** Display the LLM-generated summary of submission clusters. Inform users they can get the full list via DM command (`/view_results <proposal_id>`).
    *   **FR5.4:** (Optional v0, Core v1) DM proposer/voters with results. (Deadline reminders are v1).

**5.6. Information & History**
    *   **FR6.1:** `/my_submissions` (or `/my_votes`) command (DM): Show list of proposals user voted on/submitted to and their `response_content`.
    *   **FR6.2:** `/proposals open` command (DM): List open proposals with titles and deadlines. (Future: could be filtered by channel if multi-channel is active).
    *   **FR6.3:** `/proposals closed` command (DM): List closed proposals with titles and outcomes. (Future: could be filtered by channel).
    *   **FR6.4:** `/view_results <proposal_id>` command (DM): For closed proposals, lists all anonymized text submissions (if freeform) or breakdown of votes (e.g. "30% A, 70% B") for multiple-choice.

**5.7. Contextual Information (RAG)**
    *   **FR7.1 (Admin/Proposer - Adding General/Specific Docs):**
        *   Admin: `/add_global_doc <URL or paste text>` command (DM): Admin uploads general document content. (Future: could specify if a doc is for a specific channel or global).
        *   Proposer: Can use `/add_doc <proposal_id>` (see FR2.5) to add documents specific to their proposal.
        *   Bot processes text (chunking, embedding) and stores in vector database & SQL `Document` table (linking to `proposal_id` if applicable, or marked as global if from admin). The full text content is also stored directly for later viewing.
    *   **FR7.1.A (Admin - Managing Global Docs):**
        *   `/view_global_docs` (DM): Admin lists all global documents (ID, title).
        *   `/edit_global_doc <document_id>` (DM): Admin edits a global document. Bot may initiate a conversation for new content. Updates `raw_content` and re-processes for vector DB.
        *   `/delete_global_doc <document_id>` (DM): Admin deletes a global document. Removes from `Document` table and vector DB.
    *   **FR7.2 (User):** `/ask <question>` or `/ask <proposal_id> <question>` command (DM): User asks a question.
        *   Bot embeds question, retrieves relevant chunks from vector DB. If `proposal_id` is provided, prioritize documents linked to that proposal. If multi-channel RAG becomes a feature, context searching might also be scoped by channel.
        *   Bot uses LLM (e.g., GPT) with retrieved context + question to generate an answer.
        *   Bot DMs answer to user, citing sources (e.g., document name/link, or "From the context provided for Proposal X") and showing relevant snippets.

    *   **FR7.3 (User - Viewing Context Documents):**
        *   `/view_docs` command (DM): Lists all authorized channels the bot is configured with, showing channel names and IDs.
        *   `/view_docs <channel_id>` command (DM): Lists all proposals (ID, title, status) within a specific authorized channel.
        *   `/view_docs <proposal_id>` command (DM): Lists all context documents (ID, title) attached to a specific proposal.
        *   `/view_doc <document_id>` command (DM): Displays the full text content of a specific context document.

**5.8. Anonymity & Privacy**
    *   **FR8.1:** Individual votes/submissions are not publicly visible or attributable to specific users before the proposal deadline.
    *   **FR8.2:** The database will link users to their votes/submissions for record-keeping and features like `/my_submissions`. This data handling should be transparently communicated to users (e.g., in a privacy note accessible via `/help` or `/privacy`).
    *   **FR8.3:** Published results for multiple-choice proposals are aggregated counts. Published results for free-form proposals are an LLM-generated summary of anonymized submissions; the full list of anonymized submissions is available via DM command.
    *   **FR8.4 (Admin Access to Voter Info):** For v0, admins can view who voted/submitted on a proposal *after* it has closed and results are published, for record-keeping and transparency. This access is logged.

**5.9. (New) Bot Configuration for Proposal Channels**
    *   **FR5.9.1 (Admin):** An admin (e.g., via DM command or a configuration file/environment variable) can define a list of 'authorized proposal channel IDs'.
    *   **FR5.9.2:** If only one `TARGET_CHANNEL_ID` is set in `.env` and no other list, it operates in single-channel mode.
    *   **FR5.9.3:** If multiple authorized channel IDs are configured:
        *   DM-initiated proposals will trigger the channel selection flow (FR2.1.B).
        *   In-channel `/propose` commands will only be processed if the command is issued in one of these authorized channels (FR2.1.C).
    *   **FR5.9.4:** The bot must be a member of any authorized channel and have permissions to read messages (for in-channel `/propose`) and post messages (for broadcasting the proposal).

**6. Non-Functional Requirements**

*   **NFR1. Usability:** Intuitive commands, clear instructions, responsive feedback.
*   **NFR2. Reliability:** High uptime. Scheduler must reliably trigger deadline processing.
*   **NFR3. Performance:** Bot responses should be timely (within a few seconds for most operations). RAG queries may take slightly longer.
*   **NFR4. Scalability:** Able to handle hundreds of users and dozens of concurrent proposals. PostgreSQL (via Supabase) is chosen for its scalability and managed nature. (Multi-channel support enhances scalability of use cases).
*   **NFR5. Security:** Bot token secured. Protection against basic spam if possible (e.g., rate limiting DM commands if it becomes an issue). Admin commands for channel configuration should be protected.
*   **NFR6. Maintainability:** Code should be well-structured, commented, and version-controlled.

--

**I. Core Components & Technology Stack**

See [techContext.md](./techContext.md) for tech stack.

See [systemPatterns.md](./systemPatterns.md) for core components and architecture. (This will need updates to reflect multi-channel logic).

**II. Data Models (Simplified - using SQLAlchemy)**

Here, submissions represent votes.

*   **`User` Table:**
    *   `telegram_id` (Integer, Primary Key): Telegram user ID.
    *   `username` (String, Nullable): Telegram username.
    *   `first_name` (String): Telegram first name.
    *   `last_updated` (DateTime): Timestamp of last interaction or update.
*   **`Proposal` Table:**
    *   `id` (Integer, Primary Key, Auto-increment)
    *   `proposer_id` (Integer, Foreign Key to `User.telegram_id`)
    *   `title` (String, Not Null)
    *   `description` (Text, Not Null)
    *   `proposal_type` (Enum/String: `"multiple_choice"`, `"free_form"`, Not Null)
    *   `options` (JSON, Nullable): For `multiple_choice`, stores a list of option strings. For `free_form`, can be NULL.
    *   **`target_channel_id` (String, Not Null): The ID of the channel where this proposal is intended to be posted/discussed (could be integer if always numeric).**
    *   `channel_message_id` (Integer, Nullable): Message ID of the proposal in the `target_channel_id`.
    *   `creation_date` (DateTime, Default current timestamp)
    *   `deadline_date` (DateTime, Not Null)
    *   `status` (Enum/String: `"open"`, `"closed"`, `"cancelled"`, Default `"open"`)
    *   `outcome` (Text, Nullable): Stores winning option for MC (or tie info), LLM-generated summary of clusters for FF, or error messages.
    *   `raw_results` (JSON, Nullable): For MC, stores vote counts per option. For FF, stores a list of all anonymized submissions.
*   **`Submission` Table:**
    *   `id` (Integer, Primary Key, Auto-increment)
    *   `proposal_id` (Integer, Foreign Key to `Proposal.id`, Not Null)
    *   `submitter_id` (Integer, Foreign Key to `User.telegram_id`, Not Null)
    *   `response_content` (Text, Not Null): For multiple_choice, stores the selected *option string* (the actual vote is identified by `option_index` during interaction). For free_form, stores the user's free-form text.
    *   `timestamp` (DateTime, Default current timestamp)
    *   *Constraint:* Unique (`proposal_id`, `submitter_id`)
*   **`Document` Table (for RAG context):**
    *   `id` (Integer, Primary Key, Auto-increment)
    *   `title` (String, Nullable): User-provided title or filename.
    *   `content_hash` (String, Nullable, Index): Hash of the document content to avoid duplicates.
    *   `source_url` (String, Nullable)
    *   `upload_date` (DateTime, Default current timestamp)
    *   `vector_ids` (JSON, Nullable): List of IDs corresponding to chunks in the vector database.
    *   `proposal_id` (Integer, Foreign Key to `Proposal.id`, Nullable): Links document to a specific proposal. If NULL, it might be a global document.
    *   `raw_content` (Text, Nullable): Stores the raw (or cleaned) text content of the document.
    *   **(Future)** `associated_channel_id` (String, Nullable): If a document is context for a specific channel rather than a proposal.
    *   *(Raw content might be stored here or only in the vector DB's document store if it has one. Content can originate from direct uploads (URL/text by admin using `/add_global_doc` or proposer using `/add_doc`) or from conversational input by the proposer during proposal creation or via `/add_doc`.)*
*   **(New) `AuthorizedChannel` Table (Conceptual for FR5.9 - could also be config-based):**
    *   `channel_id` (String, Primary Key): The Telegram channel ID.
    *   `channel_name` (String, Nullable): A human-readable name for the channel.
    *   `is_proposal_target` (Boolean, Default True): Can proposals be posted here?
    *   `allow_in_channel_initiation` (Boolean, Default True): Can `/propose` be used directly in this channel?

**III. Bot Workflow & Features**

1.  **Setup & Configuration:**
    *   Bot token from BotFather.
    *   Admin user IDs.
    *   **(New/Modified)** Configuration for authorized proposal channels (e.g., a list of channel IDs in `.env` or managed via admin commands that populate the `AuthorizedChannel` table). If only one `TARGET_CHANNEL_ID` is set in `.env` and no other list, it operates in single-channel mode.

2.  **User Registration (Implicit):**
    *   When a user interacts with the bot for the first time (e.g., `/start`), store their `telegram_id`, `first_name`, and `username` (if available) in the `User` table.

3.  **Creating a Proposal (DM to Bot):**

*   **Initiation (Flexible):**
    *   User DMs bot with `/propose [Initial Information]` (e.g., just `/propose`, or `/propose <Title>`, or `/propose <Title>; <Description>; [Options OR "FREEFORM"]`).
    *   OR User types in an *authorized* Telegram channel: `/propose [Initial Information]` (similar flexibility applies, though complex structured input directly in a channel might be less common; bot will likely engage via DM for further details if only a title is given in-channel).
*   Bot (initiates `ConversationHandler`):
    *   **Parses `[Initial Information]`.**
    *   **Collects Missing Core Details (if any):** If title, description, or options/type are not fully provided, the bot asks for them sequentially in the DM.
        *   Example: Asks for title, then description, then options/type.
    *   **Channel Determination (FR2.1.A/B/C logic, after core details are known):**
        *   If initiated in an authorized channel: Set `target_channel_id` to this channel's ID. Send DM to user: "Okay, let's continue setting up your proposal for channel '[Channel Name]'. How long..."
        *   If initiated via DM:
            *   If in single-channel mode (only one `TARGET_CHANNEL_ID` configured): Set `target_channel_id` to this default.
            *   If in multi-channel mode (multiple authorized channels configured): Bot asks user in DM: "Which channel is this proposal for?" (providing options, e.g., via inline keyboard). User selects, setting `target_channel_id`.
     *   **(Common Flow - continues in DM):**
        *   Asks: "How long should this proposal be open for voting/submissions, or until when would you like to set the deadline?"
        *   User replies with natural language (e.g., "for 2 weeks", "until next Friday at noon"). Bot uses LLM to parse this into a `deadline_date`. Confirms if ambiguous.
        *   Parses the initial command to extract title, description, proposal type (inferred or explicit), options (if any). 
        *   Validates input (title, desc, options as per FR2.2). If anything goes wrong, ask for clarity.
        *   **Asks for Additional Context:** "Great! Your proposal details are set. Do you have any extra context or background information to add? This won't appear in the public poll itself but will be very helpful if users ask questions about the proposal. You can paste text, provide a URL, or just say 'no' for now."
        *   **Handles Context Response:**
            *   If "no": Proceeds.
            *   If text/URL provided: Processes and stores this context (chunking, embedding, saving to `Document` table, linked to the `proposal_id`). The `Document.source_url` might be set to indicate "proposer_chat_on_creation" or similar.
        *   Determines `proposal_type`: `"multiple_choice"` if options are provided, `"free_form"` if "FREEFORM" keyword is used or if options part is empty/specific keyword.
        *   Stores the proposal in the `Proposal` table with `status="open"`, calculated `deadline_date`, and the determined `proposal_type`.
        *   Sends a confirmation DM to the proposer: "Understood. Your proposal ID is `[proposal_id]`. It will be posted to the channel shortly. If you think of more context to add later, you can always DM me: `/add_doc <proposal_id> <URL or paste text>`."
        *   **Posts to Channel:**
            *   **For `multiple_choice` proposals:**
                *   Message: "📢 **New Proposal: [Title]**

Proposed by: @username (or First Name)

*[Description]*

Options:
1️⃣ [Option 1]
2️⃣ [Option 2]
...

Voting ends: [Date & Time]

👇 Vote Below 👇"
                *   Inline Keyboard: Buttons for each option. Callback data: `vote_[proposal_id]_[option_index]`.
            *   **For `free_form` proposals:**
                *   Message: "📢 **New Idea Collection: [Title]**

Proposed by: @username (or First Name)

*[Description]*

This is a free-form submission. To submit your idea, DM me (the bot) with:
`/submit [proposal_id] Your idea here` (Proposal ID: `[proposal_id]`)

Submissions end: [Date & Time]"
                *   Inline Button: A button like "💬 Submit Your Idea" using `switch_inline_query_current_chat` to prefill `/submit [proposal_id] ` in the user's DM with the bot.
        *   Stores the `channel_message_id` from the sent message in the `Proposal` table.


4.  **Voting (for Multiple Choice) & Submitting (for Free Form):**

    *   **A. Multiple Choice Voting (via Inline Keyboard in Channel):**
        *   User clicks an option button on a multiple-choice proposal message in the channel.
        *   Bot receives a `CallbackQuery`.
        *   Bot:
            *   Extracts `proposal_id` and `selected_option_index` from callback data.
            *   Checks if the proposal (ID from callback) is still "open" and is of `proposal_type="multiple_choice"`.
            *   Looks up the `selected_option_string` using the `selected_option_index` from the proposal's stored `options`.
            *   Checks if the user has already submitted for this proposal. If so, update their `response_content` with the new `selected_option_string`. If not, record a new submission.
            *   Stores the vote in the `Submission` table (linking `submitter_id`, `proposal_id`, and the `selected_option_string` as `response_content`).
            *   Responds to the `CallbackQuery` with a silent acknowledgment or an ephemeral message like "Your vote for '[Option]' has been recorded. You can change it until the deadline."

    *   **B. Free-Form Submission (via DM to Bot):**
        *   User DMs the bot: `/submit <proposal_id> <Their free-form text response>`
        *   Bot:
            *   Parses `proposal_id` and the free-form text.
            *   Checks if the proposal (ID from command) exists, is still "open", and is of `proposal_type="free_form"`.
            *   Checks if the user has already submitted for this proposal. If so, update their `response_content`. If not, record a new submission.
            *   Stores the submission in the `Submission` table (linking `submitter_id`, `proposal_id`, and the `free_form_text` as `response_content`).
            *   Sends a confirmation DM to the user: "Your submission for proposal #[proposal_id] has been recorded. You can change it until the deadline."

5.  **Deadline Management & Announcing Results:**
    *   **Scheduler (`APScheduler`):** Runs a job periodically (e.g., every few minutes).
    *   Job Logic:
        *   Fetches proposals where `status="open"` AND `deadline_date` has passed.
        *   For each such proposal:
            *   Change `proposal.status` to "closed".
            *   **If `proposal.proposal_type == "multiple_choice"`:**
                *   Tally votes from the `Submission` table for this `proposal_id`.
                *   Determine the outcome (e.g., option with most votes wins, or details of a tie).
                *   Store the `outcome` (e.g., "Option A passed", or "Tie: Option A & B") and `raw_results` (e.g., `{"Option A": 10, "Option B": 10, "Option C": 5}`) in the `Proposal` table.
                *   **Post Results to the proposal's target_channel_id:** Edit the original proposal message or send a new message replying to it.
                    *   Message: "🏁 **Proposal Closed: [Title]**

Results:
- [Option 1]: X votes (Y%)
- [Option 2]: A votes (B%)
...

🏆 **Outcome: [Winning Option or Tie Details]**"
            *   **If `proposal.proposal_type == "free_form"`:**
                *   Retrieve all `response_content` from `Submission` table for this `proposal_id`.
                *   Use LLM to cluster submissions and generate a summary. Store this summary as `outcome` and the full list of submissions in `raw_results`.
                *   **Post Results to Channel:**
                    *   Message: "🏁 **Idea Collection Closed: [Title]**

Thank you for your submissions! Here's a summary of the ideas received:

[LLM Generated Summary of Clusters]

To see all submissions, DM me: `/view_results [proposal_id]`"
            *   (Optional v0, Core v1) DM proposers/submitters with the outcome. (Deadline reminders are v1).

6.  **Viewing Proposals & Submission History (DM to Bot):**
    *   `/my_submissions` (or `/my_votes`): Shows a list of proposals the user submitted to, their `response_content`, and the proposal status/outcome.
    *   `/proposals open`: Lists open proposals (both types) with titles and deadlines.
    *   `/proposals closed`: Lists closed proposals (both types) with titles and outcomes. (Future enhancement: allow filtering by channel if many channels are used).
    *   `/view_results <proposal_id>`: For closed proposals, lists all anonymized submissions (freeform) or vote results (MC).
    *   `/view_docs`: Lists authorized channels the bot is configured with (useful for discovering `channel_id`).
    *   `/view_docs <channel_id>`: Lists proposals within a given channel (useful for discovering `proposal_id`).
    *   `/view_docs <proposal_id>`: Lists context documents attached to a specific proposal (useful for discovering `document_id`).
    *   `/view_doc <document_id>`: Displays the full text content of a specific document.

7.  **Getting Info on a Policy (RAG - DM to Bot):**
    *   **Admin/Proposer Command to Add Context:**
        *   Admin: `/add_global_doc <URL or paste text>` (for general documents). Admins can also use `/view_global_docs`, `/edit_global_doc <document_id>`, and `/delete_global_doc <document_id>` to manage these.
        *   Proposer: `/add_doc <proposal_id> <URL or paste text OR trigger chat with bot>` (for proposal-specific documents, can be used after initial creation or if context wasn't added during the creation flow). Proposers can also use `/edit_doc <document_id>` and `/delete_doc <document_id>` for documents they added to their proposals.
        *   *Context can also be added by the proposer conversationally during the initial proposal setup flow.* (As described in section III.3)
        *   Bot downloads/receives text.
        *   Generates embeddings for chunks of the text.
        *   Stores text chunks and embeddings in the vector DB (and metadata in `Document` SQL table, including `proposal_id` if applicable).
    *   **User Query:** `/ask <your question about a policy or topic>` or `/ask <proposal_id> <your question>`
        *   Example: `/ask What was decided about guest access policy?`
        *   Example: `/ask [proposal_id] What are the main counterarguments to this proposal?`
    *   Bot:
        *   Generates an embedding for the user's question.
        *   Queries the vector DB to find the most similar document chunks. If `proposal_id` is specified, relevant proposal-specific documents are prioritized.
        *   Constructs a prompt for the LLM (e.g., OpenAI) including retrieved context and the user's question.
        *   Sends prompt to LLM, gets the answer, and DMs it to the user, citing sources/snippets.
        * (Future enhancement: RAG could be made channel-aware if documents are associated with specific channels).

**IV. Future: Personalized Recommendations**

1.  **Gathering More Personalized Context (Requires User Consent & Privacy Considerations):**
    *   **Explicit Preferences:** `/set_preference <topic> <stance>` (e.g., `/set_preference remote_work strongly_for`)
    *   **Chat History (Very sensitive):** If users opt-in to let the bot process *their DMs with the bot* (not general chats), it could extract themes. This is technically complex and has huge privacy hurdles.
    *   **User-Uploaded Docs:** Similar to policy docs, but private to the user.

2.  **Recommendation Logic:**
    *   When a new proposal is created:
    *   Bot analyzes the proposal text (title, description).
    *   Compares it (semantically, using embeddings) to:
        *   User's past voting history (e.g., "User often votes for proposals related to X").
        *   User's explicit preferences.
        *   User's private documents (if RAG is extended to these).
    *   Uses an LLM to synthesize a recommendation:
        *   "Based on your past vote for 'Proposal Y' and your stated preference for 'Z', you might lean towards 'Option A' for this new proposal because [reasoning]."
    *   This recommendation could be DMed to the user shortly after a new proposal is posted or if they explicitly ask `/recommend <proposal_id>`.


**VI. Key Considerations & Next Steps**

1.  **Start Small (MVP):**
    *   Focus on the current single `TARGET_CHANNEL_ID` implementation first.
    *   Then, phase in multi-channel:
        *   Phase 1 (Multi-channel): Allow DM proposal creation with channel selection from a pre-configured list. Add `target_channel_id` to `Proposal` model.
        *   Phase 2 (Multi-channel): Implement in-channel `/propose` for authorized channels.
        *   Phase 3 (Multi-channel): Admin commands to manage authorized channels.
    *   Focus on `/propose` (with conversational duration), channel posting, inline voting (MC), `/submit` (FF), `/cancel_proposal`, `/edit_proposal`, `/add_doc <proposal_id>`, deadline checking, and result announcement first.
    *   Use PostgreSQL (via Supabase) with Alembic for migrations.
    *   Manual document loading for RAG initially by admin (`/add_global_doc`); proposers can add context to their proposals (`/add_doc <proposal_id>`).
2.  **Error Handling & User Feedback:** Make the bot responsive. Inform users if their commands are malformed, if LLM parsing of duration is ambiguous, if something goes wrong, etc.
3.  **Security:**
    *   Your `TOKEN` is sensitive. Use environment variables or a config file (not committed to Git).
    *   Consider who can create proposals or add documents. Proposers can add context to their own proposals. Admins manage general docs.
    *   Admin commands for managing authorized channels need to be secured.
4.  **Privacy:**
    *   Votes are anonymous *until published*. The bot DB will have the voter-to-vote mapping. Be clear about this in the `/privacy` command. Admin access to this mapping is for post-closure record-keeping.
    *   Personalized recommendations based on chat history are a *major* privacy concern. Proceed with extreme caution and explicit, granular consent if you ever go down that path.
5.  **Scalability:** PostgreSQL is a good choice for future growth.
    * (Note) Multi-channel improves use-case scalability.
6.  **Deployment:** You can run this on a small VPS, a Raspberry Pi (if local LLMs aren't used heavily), or cloud platforms like Heroku/Railway/Fly.io.
7.  **Refinement (Post-v0 / v1):**
    *   Deadline reminders.
    *   More sophisticated admin moderation tools (banning, editing any proposal etc.).
    *   More sophisticated voting options (e.g., ranked choice - much more complex).
    *   DM proposers/voters with results becomes a core feature.

