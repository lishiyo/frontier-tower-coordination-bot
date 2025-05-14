# PRD: CoordinationBot (v0)

We are building a Telegram bot called `CoordinationBot` for policy proposals and voting at Frontier Tower, with RAG for context and future personalized recommendations.

This document outlines the product requirements for `CoordinationBot`, which is designed to facilitate policy proposals, idea generation, voting, and information dissemination within the community. The bot will allow members to create proposals, vote on predefined options or submit free-form responses, access contextual information about policies, and (in the future) receive personalized voting recommendations.

**Core features (v0):
- you can DM the bot to create policy proposals like "what kind of events should we do" and then it will post your proposal in a channel and people can vote on it
- it will store everyone's voting history, the proposals, the proposals outcomes and so on
- the answers can be free-form, it's not always select a single option (for example for "what kind of events should we do", that's fill-in)
- The votes should be anonymous, you can't see other people's votes until the deadline has passed and results are published.
- You should be able to DM the bot for more info on what the policy is about. Proposers can add detailed context (documents/chat with bot) specific to their proposals, which the bot will use. The bot can also DM the original proposal poster with questions if general context is insufficient.
    - the original proposal poster can also ask the bot to post in the full public channel about an update, in order to clarify a question for everyone
- in the future (v1) it should also be plugged into more context specific to you (chats with you, your own docs etc) beyond just your voting history, so it could recommend you how to vote as well

**User Stories**

*   **As a Proposer, I want to:**
    *   Create a new policy proposal with a title, description, and a set of predefined voting options or a free-form option. The bot will then ask me for the voting deadline (which I can specify as a duration or an end date/time), so that the community can vote on it.
    *   Create a new idea generation proposal with a title and description, asking for free-form text input from members. The bot will ask me for the submission deadline (which I can specify as a duration or an end date/time), so I can gather diverse ideas.
    *   Be notified when my proposal is created and when its deadline passes and results are published.
    *   Be able to add more context about my proposal to the bot (e.g., by uploading a document or chatting with the bot about it), so users asking about my proposal can get more detailed information.
    *   Be able to edit the title, description, or options of my proposal if no votes have been cast yet.
    *   Be able to cancel my active proposals before their deadline.
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
    *   View all closed proposals and their outcomes (including aggregated vote counts or a list of free-form submissions).
    *   DM the bot to ask questions about existing policies or context documents and receive relevant answers.
*   **As an Admin/Moderator, I want to:**
    *   Upload and manage general context documents (e.g., existing policies, guidelines) that the bot can use to answer questions.
    *   Invite the bot to channels.
    *   View all proposals, their outcomes, and (after results are published) who submitted/voted for transparency and record-keeping (for v0).
    *   (Future v1) Cancel or moderate any proposals, edit proposals, extend deadlines, close proposals early, or ban users.
*   **As a Future User (with consent), I want to:**
    *   Receive personalized recommendations on how to vote based on my past voting history and other relevant personal context (my documents, chats with the bot).

**5. Functional Requirements**

**5.1. Core Bot Interaction & User Management**
    *   **FR1.1:** Bot accessible via Telegram DM and posts to a designated Telegram Channel.
    *   **FR1.2:** Implicit user registration: store `telegram_id`, `first_name`, `username` (if available) on first interaction.
    *   **FR1.3:** `/start` command: Welcome message.
    *   **FR1.4:** `/help` command: Display available commands and usage (including `/privacy`).
    *   **FR1.5:** `/privacy` command (DM): Displays the bot's privacy policy, outlining data storage, usage, and anonymity aspects.

**5.2. Proposal Creation**
    *   **FR2.1 (Proposing):**
        *   User DMs bot: `/propose <Title>; <Description>; [Options OR "FREEFORM"]`
        *   Example (Multiple Choice): `/propose Event Types; What kind of events?; Hackathons, Talks, Socials`
        *   Example (Free Form): `/propose AI Project Ideas; Suggest cool AI projects!`
        *   Bot will then ask: "How long should this proposal be open for voting/submissions, or until when would you like to set the deadline?"
        *   User provides a natural language response (e.g., "7 days", "until May 21st at 5 PM", "for 3 weeks").
        *   The bot will use an LLM to parse this response and determine the `deadline_date`. Bot confirms interpretation with user if ambiguous.
        *   **Bot then asks:** "Great! Your proposal details are set. Do you have any extra context or background information to add? This won't appear in the public poll itself but will be very helpful if users ask questions about the proposal. You can paste text, provide a URL, or just say 'no' for now."
        *   User responds. If context (text/URL) is provided, bot processes and stores it (see FR2.5 logic), associating it with the new proposal.
    *   **FR2.2:** Bot parses initial command, validates title, description, and options (minimum 2 options for multiple-choice). Confirms deadline interpretation with user if ambiguous, or proceeds if confident.
    *   **FR2.3:** Store proposal details in the database, including `proposal_type` ("multiple_choice" or "free_form"), proposer, creation date, LLM-parsed `deadline_date`. For multiple-choice, `options` are stored as a list of strings.
    *   **FR2.4:** Bot sends confirmation DM to proposer: "Understood. Your proposal ID is `[proposal_id]`. It will be posted to the channel shortly. If you think of more context to add later, you can always DM me: `/add_proposal_context <proposal_id> <URL or paste text>`."
    *   **FR2.5 (Adding Context - Proposer - Later or if initial offer declined):** `/add_proposal_context <proposal_id> <URL or paste text OR trigger chat>` (DM)
        *   Allows proposer to upload a document, paste text, or engage in a short chat with the bot to add context to their specific proposal *after* initial creation or if they initially declined to add context.
        *   This content is processed (chunked, embedded) and stored, linked to the `proposal_id` in the `Document` table, for use in RAG when users ask about this proposal. If text is from chat, `source_url` in `Document` table might indicate "proposer_chat_context".

**5.3. Proposal Broadcasting & Interaction**
    *   **FR3.1:** Bot posts new proposal to designated Telegram Channel.
        *   **Multiple Choice:** Message includes title, description, proposer, deadline, and inline keyboard buttons for each voting option. Callback data for buttons includes `proposal_id` and `option_index` (0-based index of the option).
        *   **Free Form:** Message includes title, description, proposer, deadline, and clear instructions on how to submit via DM (e.g., "DM me `/submit <proposal_id> Your idea here`"). Proposal ID should be clearly visible. May include a `switch_inline_query_current_chat` button to prefill the `/submit` command.
    *   **FR3.2:** Store `channel_message_id` for future updates (e.g., posting results).

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
        *   If edited, bot updates the proposal message in the channel.
    *   **FR4.5 (Proposal Cancellation - Proposer):** `/cancel_proposal <proposal_id>` (DM)
        *   Allows proposer to cancel their own proposal if its `status` is "open".
        *   Bot updates proposal `status` to "cancelled", updates the channel message (e.g., "This proposal has been cancelled by the proposer."), and notifies any existing voters/submitters via DM (optional).

**5.5. Deadline Management & Results**
    *   **FR5.1:** Automated scheduler checks for proposals past their deadline.
    *   **FR5.2:** For each expired proposal:
        *   Set proposal `status` to "closed".
        *   **Multiple Choice:** Tally votes from `Submission` table. Determine outcome. If there's a tie, the outcome reflects the tie (e.g., "Tie between Option A and Option B"). Store outcome and vote counts in `Proposal` table.
        *   **Free Form:** Retrieve all `response_content`. Use an LLM to cluster submissions and generate a summary of the main themes/clusters. Store this summary as `Proposal.outcome` and the full list of anonymized submissions in `Proposal.raw_results`.
    *   **FR5.3:** Bot posts results to the Telegram Channel (e.g., edits original message or replies to it).
        *   **Multiple Choice:** Display winning option(s) (or tie details) and vote counts/percentages for all options.
        *   **Free Form:** Display the LLM-generated summary of submission clusters. Inform users they can get the full list via DM command.
    *   **FR5.4:** (Optional v0, Core v1) DM proposer/voters with results. (Deadline reminders are v1).

**5.6. Information & History**
    *   **FR6.1:** `/my_submissions` (or `/my_votes`) command (DM): Show list of proposals user voted on/submitted to and their `response_content`.
    *   **FR6.2:** `/proposals open` command (DM): List open proposals with titles and deadlines.
    *   **FR6.3:** `/proposals closed` command (DM): List closed proposals with titles and outcomes.
    *   **FR6.4:** `/view_submissions <proposal_id>` command (DM): For closed free-form proposals, lists all anonymized text submissions.

**5.7. Contextual Information (RAG)**
    *   **FR7.1 (Admin/Proposer - Adding General/Specific Docs):**
        *   Admin: `/add_doc <URL or paste text>` command (DM): Admin uploads general document content.
        *   Proposer: Can use `/add_proposal_context <proposal_id>` (see FR2.5) to add documents specific to their proposal.
        *   Bot processes text (chunking, embedding) and stores in vector database & SQL `Document` table (linking to `proposal_id` if applicable).
    *   **FR7.2 (User):** `/ask <question>` or `/ask <proposal_id> <question>` command (DM): User asks a question.
        *   Bot embeds question, retrieves relevant chunks from vector DB. If `proposal_id` is provided, prioritize documents linked to that proposal.
        *   Bot uses LLM (e.g., GPT) with retrieved context + question to generate an answer.
        *   Bot DMs answer to user, citing sources (e.g., document name/link, or "From the context provided for Proposal X") and showing relevant snippets.

**5.8. Anonymity & Privacy**
    *   **FR8.1:** Individual votes/submissions are not publicly visible or attributable to specific users before the proposal deadline.
    *   **FR8.2:** The database will link users to their votes/submissions for record-keeping and features like `/my_submissions`. This data handling should be transparently communicated to users (e.g., in a privacy note accessible via `/help` or `/privacy`).
    *   **FR8.3:** Published results for multiple-choice proposals are aggregated counts. Published results for free-form proposals are an LLM-generated summary of anonymized submissions; the full list of anonymized submissions is available via DM command.
    *   **FR8.4 (Admin Access to Voter Info):** For v0, admins can view who voted/submitted on a proposal *after* it has closed and results are published, for record-keeping and transparency. This access is logged.

**6. Non-Functional Requirements**

*   **NFR1. Usability:** Intuitive commands, clear instructions, responsive feedback.
*   **NFR2. Reliability:** High uptime. Scheduler must reliably trigger deadline processing.
*   **NFR3. Performance:** Bot responses should be timely (within a few seconds for most operations). RAG queries may take slightly longer.
*   **NFR4. Scalability:** Able to handle hundreds of users and dozens of concurrent proposals. Database choice (SQLite initially) should allow for future migration if needed.
*   **NFR5. Security:** Bot token secured. Protection against basic spam if possible (e.g., rate limiting DM commands if it becomes an issue).
*   **NFR6. Maintainability:** Code should be well-structured, commented, and version-controlled.

--

**I. Core Components & Technology Stack**

See [techContext.md](./techContext.md) for tech stack.

See [systemPatterns.md](./systemPatterns.md) for core components and architecture.

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
    *   `channel_message_id` (Integer, Nullable): Message ID of the proposal in the channel.
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
    *   `proposal_id` (Integer, Foreign Key to `Proposal.id`, Nullable): Links document to a specific proposal.
    *   *(Raw content might be stored here or only in the vector DB's document store if it has one. Content can originate from direct uploads (URL/text by admin/proposer) or from conversational input by the proposer during proposal creation or via `/add_proposal_context`.)*


**III. Bot Workflow & Features**

1.  **Setup & Configuration:**
    *   Bot token from BotFather.
    *   Target channel ID (where proposals are posted).
    *   Admin user IDs (optional, for certain commands like `/add_doc`).

2.  **User Registration (Implicit):**
    *   When a user interacts with the bot for the first time (e.g., `/start`), store their `telegram_id`, `first_name`, and `username` (if available) in the `User` table.

3.  **Creating a Proposal (DM to Bot):**
    *   User DMs: `/propose <Title>; <Description>; [Option 1, Option 2, ... OR "FREEFORM"]`
        *   Example (Multiple Choice): `/propose Event Types; What kind of events should we do?; Hackathons, Talks, Socials`
        *   Example (Free Form): `/propose AI Project Ideas; Suggest cool AI projects for the floor!`
    *   Bot:
        *   Asks: "How long should this proposal be open for voting/submissions, or until when would you like to set the deadline?"
        *   User replies with natural language (e.g., "for 2 weeks", "until next Friday at noon"). Bot uses LLM to parse this into a `deadline_date`. Confirms if ambiguous.
        *   Parses the initial command to extract title, description, proposal type (inferred or explicit), options (if any).
        *   Validates input (title, desc, options as per FR2.2).
        *   **Asks for Additional Context:** "Great! Your proposal details are set. Do you have any extra context or background information to add? This won't appear in the public poll itself but will be very helpful if users ask questions about the proposal. You can paste text, provide a URL, or just say 'no' for now."
        *   **Handles Context Response:**
            *   If "no": Proceeds.
            *   If text/URL provided: Processes and stores this context (chunking, embedding, saving to `Document` table, linked to the `proposal_id`). The `Document.source_url` might be set to indicate "proposer_chat_on_creation" or similar.
        *   Determines `proposal_type`: `"multiple_choice"` if options are provided, `"free_form"` if "FREEFORM" keyword is used or if options part is empty/specific keyword.
        *   Stores the proposal in the `Proposal` table with `status="open"`, calculated `deadline_date`, and the determined `proposal_type`.
        *   Sends a confirmation DM to the proposer: "Understood. Your proposal ID is `[proposal_id]`. It will be posted to the channel shortly. If you think of more context to add later, you can always DM me: `/add_proposal_context <proposal_id> <URL or paste text>`."
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
                *   (Optional) Inline Button: A button like "💬 Submit Your Idea" using `switch_inline_query_current_chat` to prefill `/submit [proposal_id] ` in the user's DM with the bot.
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
                *   **Post Results to Channel:** Edit the original proposal message or send a new message replying to it.
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

To see all submissions, DM me: `/view_submissions [proposal_id]`"
            *   (Optional v0, Core v1) DM proposers/submitters with the outcome. (Deadline reminders are v1).

6.  **Viewing Proposals & Submission History (DM to Bot):**
    *   `/my_submissions` (or `/my_votes`): Shows a list of proposals the user submitted to, their `response_content`, and the proposal status/outcome.
    *   `/proposals open`: Lists open proposals (both types) with titles and deadlines.
    *   `/proposals closed`: Lists closed proposals (both types) with titles and outcomes.
    *   `/view_submissions <proposal_id>`: For closed free-form proposals, lists all anonymized submissions.

7.  **Getting Info on a Policy (RAG - DM to Bot):**
    *   **Admin/Proposer Command to Add Context:**
        *   Admin: `/add_doc <URL or paste text>` (for general documents)
        *   Proposer: `/add_proposal_context <proposal_id> <URL or paste text OR trigger chat with bot>` (for proposal-specific documents, can be used after initial creation or if context wasn't added during the creation flow)
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
    *   Focus on `/propose` (with conversational duration), channel posting, inline voting (MC), `/submit` (FF), `/cancel_proposal`, `/edit_proposal`, `/add_proposal_context`, deadline checking, and result announcement first.
    *   Use PostgreSQL with Alembic for migrations.
    *   Manual document loading for RAG initially by admin; proposers can add context to their proposals.
2.  **Error Handling & User Feedback:** Make the bot responsive. Inform users if their commands are malformed, if LLM parsing of duration is ambiguous, if something goes wrong, etc.
3.  **Security:**
    *   Your `TOKEN` is sensitive. Use environment variables or a config file (not committed to Git).
    *   Consider who can create proposals or add documents. Proposers can add context to their own proposals. Admins manage general docs.
4.  **Privacy:**
    *   Votes are anonymous *until published*. The bot DB will have the voter-to-vote mapping. Be clear about this in the `/privacy` command. Admin access to this mapping is for post-closure record-keeping.
    *   Personalized recommendations based on chat history are a *major* privacy concern. Proceed with extreme caution and explicit, granular consent if you ever go down that path.
5.  **Scalability:** PostgreSQL is a good choice for future growth.
6.  **Deployment:** You can run this on a small VPS, a Raspberry Pi (if local LLMs aren't used heavily), or cloud platforms like Heroku/Railway/Fly.io.
7.  **Refinement (Post-v0 / v1):**
    *   Deadline reminders.
    *   More sophisticated admin moderation tools (banning, editing any proposal etc.).
    *   More sophisticated voting options (e.g., ranked choice - much more complex).
    *   DM proposers/voters with results becomes a core feature.


# Implementation Milestones and Testing Plan

Here's a structured approach to testing our `CoordinationBot`:

**I. Test Environment Setup**

1.  **Separate Test Bot:**
    *   Go to BotFather on Telegram.
    *   Create a *new* bot specifically for testing (e.g., `FrontierTowerTestBot`). Get its API token.
    *   **Crucially, use this test token in your development environment.** Do not use your production bot token for testing.

2.  **Test Channel:**
    *   Create a new private Telegram channel (e.g., "FT Bot Test Channel").
    *   Add your `FrontierTowerTestBot` to this channel as an administrator. Make sure it has permissions to post messages.
    *   Get the Channel ID. You can do this by:
        *   Forwarding a message from the channel to a bot like `@JsonDumpBot` or `@userinfobot`. The `chat.id` in the forwarded message's JSON will be your channel ID (it's usually a negative number).
        *   Temporarily making the channel public, using its `@username` and then converting it to ID using another bot, then making it private again.

3.  **Test Users:**
    *   You will be one test user.
    *   Ideally, get 1-2 colleagues or friends to act as other test users. This helps test multi-user interactions and ensures things look right from different perspectives. They will need to DM your `FrontierTowerTestBot`.

4.  **Test Database:**
    *   Ensure your bot script connects to a separate database for testing (e.g., `frontier_tower_test.db` if using SQLite). You don't want to pollute your production database with test data.
    *   Have an easy way to wipe and reset this test database.

5.  **Local RAG Setup:**
    *   Use a local vector database (like ChromaDB running in-memory or with local persistence) for testing the `/ask` functionality.
    *   Prepare a few sample documents to load for context.

**II. Testing Phases & What to Test**

**Phase 1: Basic Bot Interaction & Setup**

*   **`/start` command:**
    *   DM your test bot `/start`.
    *   Verify: You receive the welcome message. Your user info is (implicitly) added to the test database.
*   **Help command (`/help`):**
    *   Verify: You receive a list of available commands.
*   **Invalid commands:**
    *   Send a random command like `/fooobar`.
    *   Verify: The bot responds gracefully (e.g., "Unknown command. Try /help.").

**Phase 2: Proposal Creation Workflow**

*   **Valid Proposal:**
    *   DM test bot: `/propose Test Event; Let's decide on a test event; Workshop, Social Gathering, Demo Day; 1` (short duration for quick testing).
    *   Verify (Proposer's DM): You receive a confirmation message.
    *   Verify (Database): A new proposal entry exists with correct title, description, options, proposer ID, status "open", and calculated deadline.
    *   Verify (Test Channel):
        *   A new message is posted by the bot.
        *   The message format is correct (title, proposer, description, options, deadline).
        *   An inline keyboard with the voting options ("Workshop", "Social Gathering", "Demo Day") is present.
*   **Invalid Proposal Formats:**
    *   `/propose Missing parts; Description only`
    *   `/propose Title; Desc; Opt1,Opt2; NotANumberForDays`
    *   `/propose Title; Desc; OnlyOneOption; 1`
    *   Verify: The bot DMs you an error message explaining the issue. No proposal is created in the DB or posted to the channel.

**Phase 3: Voting Workflow**

*   **First Vote:**
    *   In the test channel, as Test User 1, click the "Workshop" button on the proposal message.
    *   Verify (Voter's side): You receive a "vote recorded" ephemeral message (or a DM if you design it that way). The inline keyboard might disappear or update.
    *   Verify (Database): A new vote entry exists linking your `telegram_id` to the proposal ID and "Workshop".
    *   Verify (Anonymity): No public message in the channel indicates *who* voted or *what* they voted for.
*   **Second Vote (Different User):**
    *   As Test User 2 (or yourself using a different Telegram account if possible, or just simulate by changing `user_id` in your test script if you're only one person), click "Social Gathering".
    *   Verify (Database): Another vote entry for the same proposal, different user, different option.
*   **Changing a Vote:**
    *   As Test User 1, click "Social Gathering" on the same proposal.
    *   Verify (Database): The existing vote for Test User 1 for that proposal is updated to "Social Gathering" (or you have logic to prevent/allow changes and test that).
*   **Voting on a Closed Proposal (Test later after deadline passes):**
    *   Attempt to vote.
    *   Verify: Vote is rejected, user is notified.

**Phase 4: Deadline Management & Results Announcement**

*   **Let Deadline Pass:**
    *   Wait for the short (e.g., 1 day, or even 5 minutes for quick testing, by setting a deadline in the near past) deadline of your test proposal to pass.
    *   Ensure your scheduler (`APScheduler` or `JobQueue`) is running.
*   **Verify (Database):**
    *   The proposal's `status` is changed to "closed".
    *   The `outcome` field is populated correctly based on the votes (e.g., "Social Gathering wins with 2 votes").
*   **Verify (Test Channel):**
    *   The bot posts a results message.
    *   The results message should clearly state the outcome and the vote counts/percentages for each option.
    *   It might edit the original proposal message or reply to it.

**Phase 5: Information Retrieval (RAG)**

*   **Add Documents:**
    *   Use an admin command (`/add_doc <URL or text>`) to feed 2-3 sample policy documents into the bot's context.
    *   Verify (Database/VectorDB): Documents are processed and stored/indexed.
*   **Ask Questions:**
    *   DM test bot: `/ask What is our policy on snacks?` (assuming "snacks" is in one of your test docs).
    *   Verify: Bot responds with relevant information from the document.
    *   DM test bot: `/ask What is the meaning of life?` (assuming this is NOT in your docs).
    *   Verify: Bot responds with "I don't have enough information..." or similar.
    *   DM test bot: `/ask Tell me about the event policy.`
    *   Verify: Bot provides a summary or relevant snippets.

**Phase 6: User Data & History**

*   **`/myvotes`:**
    *   DM the bot this command.
    *   Verify: It lists the proposals you (Test User 1) voted on and what your vote was.
*   **`/proposals open`:**
    *   Verify: It lists any proposals still open for voting.
*   **`/proposals closed`:**
    *   Verify: It lists the "Test Event" proposal with its outcome.

**III. Automated Testing (Python `unittest` or `pytest`)**

While manual end-to-end testing is vital for Telegram bots, you should also write unit tests for your core logic that *doesn't* directly involve the Telegram API.

*   **Command Parsing:** Test the functions that parse arguments from commands like `/propose`.
*   **Date Calculations:** Test deadline calculation logic.
*   **Vote Tallying:** Test the function that takes a list of votes and determines the winner.
*   **RAG Logic (without LLM calls):** If you have functions that prepare prompts or process LLM output, test those.
*   **Database Interactions:** You can test your SQLAlchemy models and basic CRUD operations (though this can sometimes bleed into integration testing). Mock the database session for pure unit tests.

**Example `pytest` structure (conceptual):**

```python
# tests/test_proposal_logic.py
from your_bot_module.db_models import Proposal
from your_bot_module.commands import parse_propose_command # Fictional function

def test_parse_propose_valid():
    args = "Event Title; Event Description; Option A,Option B; 7".split(";")
    parsed = parse_propose_command_parts(args) # Your parsing logic
    assert parsed['title'] == "Event Title"
    assert parsed['duration_days'] == 7
    assert len(parsed['options']) == 2

def test_tally_votes():
    from your_bot_module.scheduler_jobs import _tally_proposal_votes # Fictional
    mock_votes = [
        {'selected_option': 'A'}, {'selected_option': 'B'}, {'selected_option': 'A'}
    ]
    mock_options = ['A', 'B', 'C']
    outcome, counts = _tally_proposal_votes(mock_votes, mock_options)
    assert outcome == 'A'
    assert counts['A'] == 2
    assert counts['B'] == 1
```

**Key Tips for Testing:**

*   **Iterate:** Test features as you build them, not just at the very end.
*   **Logging:** Use Python's `logging` module extensively. `logger.info()`, `logger.debug()`, `logger.error()` will be invaluable for seeing what your bot is doing internally, especially when it's running on a server.
*   **Clean State:** Ensure you can easily reset your test database and vector store between test runs for consistent results.
*   **Patience:** Testing interactive systems like bots can be time-consuming but is crucial for a good user experience.
