# Active Context - Mon May 19 17:16:10 PDT 2025

## Current Work Focus
- Successfully enhanced the `/ask` command by implementing interactive "View Source" buttons for displayed document references.
- This improves user experience by allowing direct access to source documents through clickable buttons rather than having to type document IDs manually.
- Implemented callback handling for these buttons using `CallbackQueryHandler` in `main.py` and a `view_doc_button_callback` function.
- Refactored document viewing functionality to reduce code duplication by creating a shared `_display_document_content` helper function used by both the `/view_doc` command and button callbacks.

## What's Working
- The `/ask` command now returns answers with interactive "View Source" buttons for each referenced document.
- Both the `/view_doc` command and the new "View Source" buttons use the same core logic through the shared `_display_document_content` helper function.
- The document management system is properly organized with document-related handlers moved to `app/telegram_handlers/document_command_handlers.py`.

## What's Broken or Pending
- **Task 5.2 Follow-ups (Still Pending from previous context):**
    - **Timezone Consistency:** Review and ensure all *other* user-facing datetimes are consistently displayed in PST.
    - **Results Message Copy:** Tweak results message copy in `ProposalService` for channel announcements from "(DM the bot)" to "(DM @botname)".
- **Current Enhancements Needed:**
    - When viewing a document from a URL source, the source URL should be displayed in the header.
    - Source buttons for URL documents should link directly to the original URL rather than showing stored content.

## Active Decisions and Considerations
- We're continuing to improve user experience by making document sources more accessible and enhancing the intuitiveness of the interface.
- For documents sourced from URLs, we're considering adding direct linking to maintain proper attribution and allow users to access the original source easily.

## Important Patterns and Preferences
- Shared helper functions for common functionality (like `_display_document_content`) help maintain code consistency and reduce duplication.
- Callback handlers are organized based on functionality, with document-related handlers in the document handlers file.

## Learnings and Project Insights
- Telegram's callback query system provides a powerful way to create interactive elements in bot messages.
- Proper refactoring and organization of command handlers improves maintainability as the bot's functionality grows.
- For document sources from URLs, providing direct attribution and access to original sources enhances transparency and usability.

## Current Database/Model State
- No database schema changes were made in this iteration. The improvements focused on enhancing the user interface and interaction patterns for existing functionality.