# Enhanced `/ask` Command: Natural Language Querying of Proposals

## 1. Introduction

This document outlines the strategy for enhancing the `/ask` command in CoordinationBot. The goal is to allow users to ask natural language questions about proposals (e.g., their status, content, deadlines, or a combination of these) and receive relevant, synthesized answers. This goes beyond the current RAG capabilities for general documents by specifically targeting and intelligently querying proposal data.

## 2. Core Idea

The enhanced `/ask` command will use a **hybrid querying approach**:

1.  **Natural Language Understanding (NLU):** An LLM will first analyze the user's query to determine intent (querying proposals vs. general documents) and extract key entities (keywords for content search, structured filters like dates, statuses, types).
2.  **Structured Filtering:** If proposal-related and structured filters are identified, a SQL query will be performed against the `proposals` table to narrow down candidates.
3.  **Semantic Content Search:** Keywords/concepts extracted by the NLU will be used to perform a semantic search against indexed proposal titles and descriptions (stored in a dedicated ChromaDB collection). This search will be applied to the results of the structured filtering if applicable.
4.  **Response Synthesis:** An LLM will generate a natural language response based on the proposals retrieved from the combined querying steps.

## 3. Detailed Implementation Steps

### Step 1: User Interaction & Initial Parsing
*   The user sends `/ask <natural language query>` via DM.
*   The `CommandHandlers.handle_ask_question` function in `app/telegram_handlers/command_handlers.py` receives the full query string.

### Step 2: Intent Analysis & Disambiguation
*   This logic will reside primarily within `ContextService` (or a new dedicated `AskService` if complexity grows).
*   `ContextService.handle_intelligent_ask(query_text)` will be the entry point.
*   It will call `LLMService.analyze_ask_query(query_text)` (a new or modified LLM service method).
    *   **Prompt Engineering:** This LLM call will use a carefully crafted prompt instructing the LLM to:
        1.  Determine the primary intent: Is the user asking about **proposals** or **general documents** (current RAG)?
        2.  If the intent is proposal-related, extract:
            *   `content_keywords` (string): Keywords or phrases for semantic search within proposal text (e.g., "pizza party," "budget review," "event ideas").
            *   `structured_filters` (dictionary/object):
                *   `status`: (e.g., "open," "closed," "cancelled")
                *   `date_query`: Natural language date phrase (e.g., "last week," "in July 2024," "before May 10th"). This will need further parsing into actual dates.
                *   `proposal_type`: (e.g., "multiple_choice," "free_form")
                *   *(Future considerations: proposer, target_channel_id)*
    *   If the intent is determined to be general document querying, `ContextService` will proceed with the existing RAG flow.

### Step 3: Proposal Query Execution (if intent is proposal-related)

#### Step 3.1: Indexing Proposals for Semantic Search (Prerequisite)
*   This logic will be added to `ProposalService`.
*   **On Proposal Creation/Update:** When a proposal is successfully created (in `ProposalService.create_proposal`) or its title/description is updated (in `ProposalService.edit_proposal_details`):
    1.  Concatenate relevant text: `proposal_text_to_index = proposal.title + " " + proposal.description`.
    2.  Generate embedding: `embedding = LLMService.generate_embedding(proposal_text_to_index)`.
    3.  Store in ChromaDB via `VectorDBService.add_proposal_embedding(proposal_id, proposal_text_to_index, embedding, metadata)`:
        *   **Collection Name:** `proposals_content` (or similar).
        *   **ChromaDB ID:** `f"proposal_{proposal.id}"`.
        *   **Document:** The `proposal_text_to_index`.
        *   **Metadata:** A dictionary containing `{"proposal_id": proposal.id, "status": proposal.status, "deadline_date_iso": proposal.deadline_date.isoformat(), "creation_date_iso": proposal.creation_date.isoformat(), "type": proposal.proposal_type, "target_channel_id": proposal.target_channel_id}`. This metadata can be useful for potential future direct filtering in ChromaDB if its capabilities are sufficient, or for enriching results.

#### Step 3.2: Parsing Date Queries
*   If `structured_filters.date_query` was extracted by the LLM, `ContextService` will use `LLMService.parse_natural_language_duration(structured_filters.date_query)` to convert it into a start and end `datetime` object or a specific date. This might require enhancements to `parse_natural_language_duration` to handle ranges or relative terms like "last week" more explicitly for querying.

#### Step 3.3: Structured Filtering (SQL)
*   `ContextService` will call a new method in `ProposalRepository`, e.g., `ProposalRepository.find_proposals_by_dynamic_criteria(status=extracted_status, date_range=(start_date, end_date), proposal_type=extracted_type)`.
*   This repository method will construct a dynamic SQL query using `SQLAlchemy` to filter proposals based on the provided criteria.
*   It will return a list of `Proposal` objects (or at least their IDs) that match the structured filters.
*   If no structured filters were extracted, this step might be skipped, or it might fetch all non-cancelled proposals as a base set if content keywords are present.

#### Step 3.4: Semantic Content Search (ChromaDB)
*   This step is performed if `content_keywords` were extracted by the LLM in Step 2.
*   `ContextService` will:
    1.  Generate query embedding: `query_embedding = LLMService.generate_embedding(content_keywords)`.
    2.  Call `VectorDBService.search_proposal_embeddings(query_embedding, top_n=X)`.
        *   This method in `VectorDBService` will search the `proposals_content` collection.
    3.  This returns a list of `proposal_id`s from ChromaDB metadata, along with similarity scores and potentially the matched text.

#### Step 3.5: Consolidating Results
*   `ContextService` will consolidate the results:
    *   If both structured filters (Step 3.3) and content keywords (Step 3.4) were used: Find the intersection of `proposal_id`s from both lists.
    *   If only structured filters were used: The results from Step 3.3 are the final candidates.
    *   If only content keywords were used: The results from Step 3.4 are the final candidates.
*   Fetch full `Proposal` objects for the final list of candidate `proposal_id`s using `ProposalRepository.get_proposals_by_ids()`.

### Step 4: Response Synthesis
*   Performed in `ContextService`.
*   **If matching proposals are found:**
    1.  Prepare a summary of the matching proposals (e.g., a list of dictionaries with title, ID, status, deadline, and potentially a link to the proposal message or channel).
    2.  Construct a prompt for `LLMService.get_completion`. The prompt will include:
        *   The user's original `query_text`.
        *   The summarized data of the matching proposals.
        *   Instructions for the LLM to synthesize a concise, natural language answer based *only* on the provided proposal data. The answer should clearly list the matching proposals and explicitly guide the user to use the `/my_vote <proposal_id>` command to see their specific submission for any of these proposals (e.g., "I found the following proposals related to your query: [List proposals]. To see your submission for a specific one, use `/my_vote <ID>`.").
    3.  The LLM generates the answer.
*   **If no proposals match:**
    *   `ContextService` will formulate a polite message like, "I couldn't find any proposals matching your query: '[user's query]'. You can try rephrasing or broadening your search."
*   **If the initial intent was ambiguous or an error occurred:**
    *   Provide a helpful message, possibly suggesting the user try `/help` or rephrase.

### Step 5: Displaying Results
*   `CommandHandlers.handle_ask_question` receives the synthesized answer (or "not found" message) from `ContextService`.
*   Sends this response to the user via DM.

## 4. Data Schema & Storage

### PostgreSQL (`proposals` table - `app/persistence/models/proposal_model.py`)
*   No schema changes are strictly required for this feature, as existing fields (`id`, `title`, `description`, `status`, `deadline_date`, `proposal_type`, `creation_date`, `target_channel_id`) will be used.
*   Ensure appropriate database indexes exist on fields commonly used for filtering (e.g., `status`, `deadline_date`, `proposal_type`, `creation_date`).

### ChromaDB (Vector Database)
*   **New Collection:** `proposals_content`
*   **Document Structure per Entry:**
    *   `id` (string): `f"proposal_{proposal.id}"` (unique identifier for the ChromaDB entry).
    *   `embedding` (vector): The embedding of `proposal.title + " " + proposal.description`.
    *   `document` (string): The concatenated `proposal.title + " " + proposal.description`.
    *   `metadata` (dictionary):
        ```json
        {
          "proposal_id": int,          // SQL primary key of the proposal
          "status": "open" | "closed" | "cancelled",
          "deadline_date_iso": "YYYY-MM-DDTHH:MM:SS", // ISO format string
          "creation_date_iso": "YYYY-MM-DDTHH:MM:SS", // ISO format string
          "type": "multiple_choice" | "free_form",
          "target_channel_id": "string_channel_id" // Or integer if applicable
        }
        ```

## 5. Key Component Changes & New Methods

### `LLMService` (`app/services/llm_service.py`)
*   **New/Modified Method:** `analyze_ask_query(query_text: str) -> dict`:
    *   Takes the raw user query.
    *   Returns a dictionary like: `{"intent": "query_proposals" | "query_general_docs", "content_keywords": "...", "structured_filters": {"status": "...", "date_query": "...", "type": "..."}}`. (The LLM no longer needs to be prompted to identify an intent to retrieve the user's specific submission within this flow).
*   Ensure `generate_embedding(text: str)` is robust.
*   `parse_natural_language_duration(text: str)` might need enhancements to reliably parse date ranges or relative queries (e.g., "last month," "next week") into start/end datetimes.

### `VectorDBService` (`app/services/vector_db_service.py`)
*   **New Method:** `add_proposal_embedding(proposal_id: int, text_content: str, embedding: list[float], metadata: dict)`:
    *   Adds/updates the proposal's text and embedding in the `proposals_content` collection.
*   **New Method:** `search_proposal_embeddings(query_embedding: list[float], top_n: int = 5, filter_proposal_ids: Optional[list[int]] = None) -> list[dict]`:
    *   Searches the `proposals_content` collection.
    *   `filter_proposal_ids`: If provided, the search results should be restricted to these proposal IDs (post-retrieval filtering if ChromaDB's direct metadata filtering is too complex for this specific combination).
    *   Returns a list of results, each containing at least `proposal_id` and `score`.
*   **New Method:** `find_proposals_by_dynamic_criteria(status: Optional[str] = None, date_range: Optional[tuple[datetime, datetime]] = None, proposal_type: Optional[str] = None, creation_date_range: Optional[tuple[datetime, datetime]] = None) -> list[Proposal]`:
    *   Constructs and executes a dynamic SQLAlchemy query based on non-None criteria.
    *   Handles date range queries for `deadline_date` and `creation_date`.
*   **New Method (for the new `/my_vote` command):** `get_submission_by_proposal_and_user(proposal_id: int, submitter_id: int) -> Submission | None` (This would actually be in `SubmissionRepository`).

### `ProposalService` (`app/core/proposal_service.py`)
*   Modify `create_proposal(...)` and `edit_proposal_details(...)`:
    *   After successfully saving/updating the proposal in the SQL database, call the new `VectorDBService.add_proposal_embedding` method to index/re-index its content.

### `ProposalRepository` (`app/persistence/repositories/proposal_repository.py`)
*   **New Method:** `find_proposals_by_dynamic_criteria(status: Optional[str] = None, date_range: Optional[tuple[datetime, datetime]] = None, proposal_type: Optional[str] = None, creation_date_range: Optional[tuple[datetime, datetime]] = None) -> list[Proposal]`:
    *   Constructs and executes a dynamic SQLAlchemy query based on non-None criteria.
    *   Handles date range queries for `deadline_date` and `creation_date`.

### `ContextService` (`app/core/context_service.py`)
*   **New/Refactored Method:** `handle_intelligent_ask(query_text: str) -> str`:
    *   This will be the main orchestrator for the enhanced `/ask` flow as described in "Detailed Implementation Steps."
    *   It will replace parts of the existing logic in `get_answer_for_question` or call it as a fallback if the intent is general documents.
*   Allowing users to specify if they *only* want to search proposals or *only* general documents.
*   Caching LLM analyses of common query types or proposal summaries.

### `CommandHandlers` (`app/telegram_handlers/command_handlers.py`)
*   Modify `ask_command` (or `handle_ask_question`):
    *   Pass the user's full query string to `ContextService.handle_intelligent_ask(query_text)`.

## 6. Error Handling & Edge Cases
*   **Ambiguous Queries:** The LLM in `analyze_ask_query` should ideally indicate ambiguity. `ContextService` might then ask the user for clarification or default to general RAG.
*   **No Matching Proposals:** Handled by `ContextService` providing a "not found" message.
*   **LLM Errors:** Implement retries/fallbacks for LLM calls; inform the user if an answer cannot be generated.
*   **Partial Matches:** If a query has both structured parts and content keywords, but only one yields results, the system should decide whether to present partial results or state that no results matched all criteria.
*   **Very Broad Queries:** Queries like "tell me about proposals" might return too many results. Implement reasonable limits (`top_n` for semantic search, potentially limiting SQL results if no strong filters). The LLM synthesizing the final answer should be prompted to be concise.

## 7. Future Enhancements
*   Filtering by proposer or `target_channel_id`.
*   More sophisticated date range understanding.
*   Allowing users to specify if they *only* want to search proposals or *only* general documents.
*   Caching LLM analyses of common query types or proposal summaries.

## 8. New Command: `/my_vote <proposal_id>`

*   **Purpose:** Allows a user to retrieve their specific vote or submission for a single proposal.
*   **Flow:**
    1.  User DMs: `/my_vote <proposal_id>`.
    2.  `UserCommandHandlers.my_vote_command` (new handler):
        *   Parses `proposal_id`.
        *   Retrieves `user_id` from the update.
        *   Calls `SubmissionService.get_user_submission_for_proposal(user_id, proposal_id)`.
    3.  `SubmissionService.get_user_submission_for_proposal(user_id, proposal_id)` (new method):
        *   Calls `ProposalRepository.get_proposal_by_id(proposal_id)` to get proposal details (e.g., title for context in the response).
        *   Calls `SubmissionRepository.get_submission_by_proposal_and_user(proposal_id, user_id)`.
        *   Formats a response: "For proposal '[Title]' (#`proposal_id`), your submission was: '[submission_content]'" or "You did not make a submission for proposal '[Title]' (#`proposal_id`)." or "Proposal #[`proposal_id`] not found or is not yet closed for viewing submissions this way."
    4.  Handler sends the formatted response to the user.
*   **New Repository Method:**
    *   `SubmissionRepository.get_submission_by_proposal_and_user(proposal_id: int, submitter_id: int) -> Submission | None`.
