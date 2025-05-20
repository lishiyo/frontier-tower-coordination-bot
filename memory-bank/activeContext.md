# Active Context - Mon May 19 18:45:13 PDT 2025

## Current Work Focus
- Implemented Task 9.5.3: Improved "missing ID" handling for commands requiring document or proposal IDs
- Enhanced the UI for commands like `/edit_proposal`, `/cancel_proposal`, and `/view_doc` to provide clear guidance to users on using `/ask` to find relevant IDs
- Used callback-based approach for search instructions rather than prefilling input, as Telegram always prepends bot username which breaks command syntax

## What's Working
- Commands requiring proposal IDs or document IDs now provide helpful, clear instructions when used without an ID
- Users can tap "Search for Proposals" or "Search for Documents" buttons to receive detailed guidance on using the `/ask` command
- The "Close" button removes the instructions when the user is done reading them
- The callback-based approach avoids issues with Telegram's bot username prefixing when using `switch_inline_query_current_chat`
- The system correctly recommends using `/ask which proposal was about...` or `/ask which doc mentioned...` to find relevant IDs

## What's Broken or Pending
- **Bug in Proposal Creation Date Filtering**:
  - When users search with `/ask which proposals were created this month`, the system correctly parses the date range but only applies it to `deadline_date_range` instead of `creation_date_range`
  - This causes the system to match proposals with deadlines in May, but not necessarily proposals created in May
  - Code comment in `handle_intelligent_ask` indicates this is a known limitation: "Add creation_date_range if LLM also extracts it for 'created last week'"
- **Task 5.2 Follow-ups (Still Pending from previous context):**
  - **Timezone Consistency:** Review and ensure all *other* user-facing datetimes are consistently displayed in PST.
  - **Results Message Copy:** Tweak results message copy in `ProposalService` for channel announcements from "(DM the bot)" to "(DM @botname)".

## Active Decisions and Considerations
- For prefilled input situations, found that Telegram buttons using `switch_inline_query_current_chat` always prepend the bot username, which breaks command syntax
- Decided to use a callback approach that shows detailed instructions with examples instead, maintaining a cleaner and more reliable user experience
- For `/ask` queries about "created" proposals, the SQL filtering logic should use `creation_date_range` parameter instead of (or in addition to) `deadline_date_range`

## Important Patterns and Preferences
- Using callbacks with detailed instructions instead of prefilled commands allows for better control over the user experience
- Including multiple examples in the search instructions helps users understand the command pattern
- The "Close" button provides a clean way to dismiss instructions when the user is done

## Learnings and Project Insights
- Telegram's `switch_inline_query_current_chat` mechanism always prepends the bot username, which can break command syntax for commands expecting a leading "/"
- Callback-based approaches provide more control over the UX compared to prefilling, at the cost of requiring users to manually type commands
- Date filtering logic should properly match the user's intent - if they ask about creation dates, we should filter by creation dates

## Current Database/Model State
- No database schema changes were made in this iteration. The improvements focused on enhancing the user interface and interaction patterns for existing functionality.