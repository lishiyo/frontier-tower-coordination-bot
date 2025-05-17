# Active Context - Sat May 17 00:02:53 PDT 2025

## Current Work Focus
- Completed Task 3.1: LLM Service Setup.
    - `app/services/llm_service.py` created.
    - `generate_embedding`, `get_completion`, and `parse_natural_language_duration` are implemented and tested.
- Preparing to start Task 3.2: VectorDB Service Setup & Document Model.

## What's Working
- `LLMService` is functional.
    - Embeddings can be generated.
    - Completions can be retrieved.
    - Natural language duration strings can be parsed into `datetime` objects using a refined LLM prompt.

## What's Broken
- No known issues related to the completed Task 3.1.

## Active Decisions and Considerations
- The prompt for `parse_natural_language_duration` was made significantly stricter to ensure the LLM returns only the date string or an error token, improving parsing reliability.

## Learnings and Project Insights
- Prompt engineering is key for reliable LLM output, especially when specific formats are required. Iterative refinement of prompts (e.g., adding constraints like "Respond with ONLY...") is often necessary.

## Current Database/Model State
- The `users` table exists.
- The `proposals` table exists and includes the `target_channel_id` (String, Not Null) column.
- No changes to DB schema in this step.

## Next Steps
- Continue with Phase 3: Conversational Proposal Creation & Initial Context.
    - Task 3.2: VectorDB Service Setup & Document Model.
        - Define `Document` SQLAlchemy model in `app/persistence/models/document_model.py`.
        - Generate Alembic migration for `Document` table and apply.
        - Create `app/persistence/repositories/document_repository.py`.
        - Create `app/services/vector_db_service.py`.
