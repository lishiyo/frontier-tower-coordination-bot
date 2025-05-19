import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI # Using AsyncOpenAI for non-blocking calls
from app.config import ConfigService
from datetime import datetime, timezone # Added timezone

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        try:
            self.api_key = ConfigService.get_openai_api_key()
            if not self.api_key:
                logger.error("OpenAI API key is not configured. LLMService will not function.")
                raise ValueError("OpenAI API key is missing.")
            self.client = AsyncOpenAI(api_key=self.api_key)
            logger.info("LLMService initialized successfully.")
        except ValueError as e:
            logger.error(f"Error initializing LLMService: {e}")
            self.client = None # Ensure client is None if initialization fails
            # Depending on strictness, could re-raise or allow degraded functionality

    async def parse_natural_language_duration(self, text: str) -> Optional[datetime]:
        """
        Parses natural language text to extract a specific deadline datetime object using an LLM.
        Example: "7 days from now", "for 3 weeks from today", "until May 21st at 5 PM", "next Monday at noon"
        Returns a timezone-aware datetime object (UTC) if successful, or None if parsing fails.
        """
        if not self.client:
            logger.error("LLMService client not initialized. Cannot parse duration.")
            return None

        # Get current time in UTC to provide as context to the LLM
        # This helps the LLM resolve relative dates like "tomorrow" or "next week"
        now_utc = datetime.now(timezone.utc)
        current_time_str = now_utc.strftime("%Y-%m-%d %H:%M:%S %Z")

        prompt = (
            f"You are a precise date parsing assistant. Your sole task is to convert user input into a specific datetime format. "
            f"Given the current time is {current_time_str}, parse the following user input to determine a future deadline date and time. "
            f"User input: '{text}'.\n"
            f"VERY IMPORTANT: Respond with ONLY the absolute date and time in the exact format 'YYYY-MM-DD HH:MM:SS UTC'. "
            f"Do NOT include any other text, explanations, or conversational phrases in your response. "
            f"Your entire response must be just the date string.\n"
            f"For example, if the current time is 2024-05-15 10:00:00 UTC and the user input is 'tomorrow at 5pm', your response must be exactly: 2024-05-16 17:00:00 UTC\n"
            f"If the input is a duration like '7 days', calculate the date 7 days from the current time ({current_time_str}) and return it in the same format.\n"
            f"If the input is too vague, clearly not a date/time, or cannot be reliably parsed into the specified format, respond with the exact string: ERROR_CANNOT_PARSE"
        )

        logger.info(f"Attempting to parse duration from text: '{text}' with current time context: {current_time_str}")

        try:
            response_text = await self.get_completion(prompt, model="gpt-4o") # Using a capable model

            if not response_text or response_text == "ERROR_CANNOT_PARSE":
                logger.warning(f"LLM could not parse duration string: '{text}'. Response: '{response_text}'")
                return None

            logger.info(f"LLM response for duration parsing of '{text}': '{response_text}'")
            
            # Attempt to parse the LLM's response into a datetime object
            # Expected format: "YYYY-MM-DD HH:MM:SS UTC"
            parsed_datetime = datetime.strptime(response_text, "%Y-%m-%d %H:%M:%S %Z")
            # Ensure it's timezone-aware (strptime with %Z should handle UTC)
            # If it somehow becomes naive, make it UTC
            if parsed_datetime.tzinfo is None:
                parsed_datetime = parsed_datetime.replace(tzinfo=timezone.utc)
            else:
                parsed_datetime = parsed_datetime.astimezone(timezone.utc) # Convert to UTC if it was parsed with another tz

            logger.info(f"Successfully parsed '{text}' to datetime: {parsed_datetime}")
            return parsed_datetime

        except ValueError as ve:
            logger.error(f"Failed to parse LLM response '{response_text}' into datetime for input '{text}': {ve}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during natural language duration parsing for '{text}': {e}", exc_info=True)
            return None

    async def generate_embedding(self, text: str, model: str = "text-embedding-3-small") -> Optional[List[float]]:
        """
        Generates an embedding for the given text using the specified OpenAI model.
        Returns a list of floats representing the embedding, or None if an error occurs.
        """
        if not self.client:
            logger.error("LLMService client not initialized. Cannot generate embedding.")
            return None
        
        try:
            text_to_embed = text.replace("\n", " ") # OpenAI recommendation
            response = await self.client.embeddings.create(input=[text_to_embed], model=model)
            embedding = response.data[0].embedding
            logger.info(f"Successfully generated embedding for text (first 50 chars): '{text[:50]}...'")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding for text '{text[:50]}...': {e}", exc_info=True)
            return None

    async def get_completion(self, prompt: str, model: str = "gpt-4o") -> Optional[str]: # Changed default to gpt-4o
        """
        Gets a completion from the OpenAI API given a prompt.
        Returns the content of the completion, or None if an error occurs.
        """
        if not self.client:
            logger.error("LLMService client not initialized. Cannot get completion.")
            return None
            
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            completion_text = response.choices[0].message.content
            logger.info(f"Successfully got completion for prompt (first 50 chars): '{prompt[:50]}...'")
            return completion_text.strip() if completion_text else None
        except Exception as e:
            logger.error(f"Error getting completion for prompt '{prompt[:50]}...': {e}", exc_info=True)
            return None

    async def cluster_and_summarize_texts(self, texts: List[str], model: str = "gpt-4o") -> Optional[str]:
        """
        Clusters a list of texts and generates a concise summary for each cluster using an LLM.
        Aims to identify 3-5 main themes or clusters.
        Returns a single string containing the summarized clusters, or None if an error occurs or no texts are provided.
        """
        if not self.client:
            logger.error("LLMService client not initialized. Cannot cluster and summarize texts.")
            return None

        if not texts:
            logger.warning("No texts provided to cluster_and_summarize_texts. Returning None.")
            return None

        # Construct the prompt for the LLM
        # Combine all texts into a single string, clearly demarcated
        numbered_texts = "\n".join([f"{i+1}. {text}" for i, text in enumerate(texts)])
        
        prompt = (
            f"You are a text analysis assistant specializing in summarizing and clustering free-form text submissions. "
            f"Below are several text submissions. Your task is to identify the main themes or clusters of ideas present in these submissions. "
            f"Aim to identify between 1 to 5 main clusters, but adjust based on the diversity of the content. "
            f"For each cluster, provide a CONCISE title or heading for the theme, followed by a BRIEF summary (1-2 sentences) of the ideas within that cluster. "
            f"If there are very few submissions or they are all very similar, it's acceptable to identify fewer clusters.\n\n"
            f"Here are the submissions:\n"
            f"{numbered_texts}\n\n"
            f"Please format your output clearly, with each cluster's title and summary. "
            f"For example:\n"
            f"Theme 1: [Cluster Title 1]\n"
            f"Summary: [Brief summary of ideas in cluster 1]\n\n"
            f"Theme 2: [Cluster Title 2]\n"
            f"Summary: [Brief summary of ideas in cluster 2]\n"
            f"..."
        )

        logger.info(f"Attempting to cluster and summarize {len(texts)} texts.")

        try:
            summary_text = await self.get_completion(prompt, model=model)

            if not summary_text:
                logger.warning("LLM returned no summary for clustering.")
                return "No summary could be generated from the submissions." # Return a placeholder

            logger.info(f"Successfully generated cluster summary for {len(texts)} texts.")
            return summary_text
        except Exception as e:
            logger.error(f"Unexpected error during text clustering and summarization for {len(texts)} texts: {e}", exc_info=True)
            return "An error occurred while generating the summary." # Return a placeholder

    async def analyze_ask_query(self, query_text: str, model: str = "gpt-4o") -> Dict[str, Any]:
        """
        Analyzes the user's /ask query to determine intent and extract relevant entities.

        Args:
            query_text: The raw text of the user's query.
            model: The LLM model to use for analysis.

        Returns:
            A dictionary containing:
            - "intent": "query_proposals" or "query_general_docs"
            - "content_keywords": Extracted keywords for semantic search (if intent is query_proposals).
            - "structured_filters": A dict with keys like "status", "proposal_type", "date_query" (if intent is query_proposals).
            - "error": An error message if parsing failed.
        """
        if not self.client:
            logger.error("LLMService client not initialized. Cannot analyze ask query.")
            return {"error": "LLMService not initialized."}

        # Get current time in UTC to provide as context for date queries
        now_utc = datetime.now(timezone.utc)
        current_time_str = now_utc.strftime("%Y-%m-%d %H:%M:%S %Z")

        prompt = f"""
        You are an expert query analysis assistant for a Telegram bot.
        Your task is to analyze the user's question and determine if they are asking about specific 'proposals'
        or if they are asking a general question that should be answered from 'general_documents'.
        If the question is about proposals, you also need to extract keywords for semantic content search and
        any structured filters like status, proposal type, or date-related queries.

        User Query: "{query_text}"
        Current UTC Time for context (if needed for date queries): {current_time_str}

        Allowed proposal statuses: "open", "closed", "cancelled"
        Allowed proposal types: "multiple_choice", "free_form"

        Output a JSON object with the following structure:
        {{
          "intent": "query_proposals" | "query_general_docs",
          "content_keywords": "string (keywords or rephrased query for semantic search, only if intent is query_proposals, otherwise null)",
          "structured_filters": {{
            "status": "string (one of the allowed statuses, or null if not specified)",
            "proposal_type": "string (one of the allowed types, or null if not specified)",
            "date_query": "string (natural language date phrase like 'last week', 'July 2024', 'before May 10th', or null if not specified)"
          }} (This whole dict is null if intent is query_general_docs)
        }}

        Examples:
        1. User Query: "what proposals closed last week?"
           Output:
           {{
             "intent": "query_proposals",
             "content_keywords": "proposals closed last week",
             "structured_filters": {{
               "status": "closed",
               "proposal_type": null,
               "date_query": "last week"
             }}
           }}
        2. User Query: "tell me about the pizza party proposal"
           Output:
           {{
             "intent": "query_proposals",
             "content_keywords": "pizza party proposal",
             "structured_filters": {{
               "status": null,
               "proposal_type": null,
               "date_query": null
             }}
           }}
        3. User Query: "how does the budget work?"
           Output:
           {{
             "intent": "query_general_docs",
             "content_keywords": null,
             "structured_filters": null
           }}
        4. User Query: "any open multiple choice proposals about funding from this month?"
           Output:
           {{
             "intent": "query_proposals",
             "content_keywords": "funding proposals",
             "structured_filters": {{
               "status": "open",
               "proposal_type": "multiple_choice",
               "date_query": "this month"
             }}
           }}
        5. User Query: "what are the active proposals?"
           Output:
           {{
             "intent": "query_proposals",
             "content_keywords": "active proposals",
             "structured_filters": {{
               "status": "open",
               "proposal_type": null,
               "date_query": null
             }}
           }}
        
        VERY IMPORTANT: Respond with ONLY the JSON object. Do NOT include any other text, explanations, or conversational phrases.
        If you cannot confidently determine the intent or extract information, lean towards "query_general_docs" or provide nulls for fields.
        Ensure the output is a valid JSON.
        """

        logger.info(f"Attempting to analyze ask query: '{query_text}'")

        try:
            # Use a model that's good at following instructions and JSON output.
            # gpt-4o or gpt-3.5-turbo with response_format={"type": "json_object"} could work.
            # For now, just using get_completion and will parse JSON manually.
            # response = await self.client.chat.completions.create(
            #     model=model,
            #     messages=[
            #         {"role": "system", "content": "You are an expert query analysis assistant. Your output must be a valid JSON object."},
            #         {"role": "user", "content": prompt}
            #     ],
            #     response_format={"type": "json_object"} # This requires newer OpenAI library versions and compatible models
            # )
            # raw_response_text = response.choices[0].message.content

            # Using existing get_completion for now, as response_format might not be set up everywhere
            raw_response_text = await self.get_completion(prompt, model=model)

            if not raw_response_text:
                logger.warning(f"LLM returned no response for ask query analysis of '{query_text}'.")
                return {
                    "intent": "query_general_docs",  # Fallback intent
                    "content_keywords": None,
                    "structured_filters": None,
                    "error": "LLM provided no response."
                }

            logger.debug(f"Raw LLM response for ask query analysis: {raw_response_text}")
            
            # Clean the response to ensure it's valid JSON (e.g., remove potential markdown backticks)
            cleaned_response_text = raw_response_text.strip()
            if cleaned_response_text.startswith("```json"):
                cleaned_response_text = cleaned_response_text[7:]
            if cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[:-3]
            cleaned_response_text = cleaned_response_text.strip()

            import json # Import json here, as it's a standard library
            parsed_response = json.loads(cleaned_response_text)
            
            # Basic validation of the parsed structure
            if not isinstance(parsed_response, dict) or "intent" not in parsed_response:
                logger.error(f"LLM response for ask query analysis was not a valid dictionary with 'intent'. Response: {cleaned_response_text}")
                return {
                    "intent": "query_general_docs", 
                    "content_keywords": None,
                    "structured_filters": None,
                    "error": "LLM response was not in the expected format."
                }
            
            # Ensure structured_filters is a dict or None if intent is not query_proposals
            if parsed_response["intent"] == "query_proposals":
                if "structured_filters" not in parsed_response or not isinstance(parsed_response.get("structured_filters"), dict):
                    parsed_response["structured_filters"] = {"status": None, "proposal_type": None, "date_query": None} # Default if missing/malformed
                if "content_keywords" not in parsed_response:
                     parsed_response["content_keywords"] = query_text # Fallback if keywords are missing
            else: # For query_general_docs
                parsed_response["content_keywords"] = None
                parsed_response["structured_filters"] = None


            logger.info(f"Successfully analyzed ask query: '{query_text}'. Intent: {parsed_response.get('intent')}")
            return parsed_response

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response for ask query analysis of '{query_text}': {e}. Response was: {cleaned_response_text}", exc_info=True)
            return {
                "intent": "query_general_docs", 
                "content_keywords": None,
                "structured_filters": None,
                "error": "Failed to parse LLM JSON response."
            }
        except Exception as e:
            logger.error(f"Unexpected error during ask query analysis for '{query_text}': {e}", exc_info=True)
            return {
                "intent": "query_general_docs",
                "content_keywords": None,
                "structured_filters": None,
                "error": f"An unexpected error occurred: {str(e)}"
            }

    async def parse_natural_language_date_range_query(self, date_query_text: str, model: str = "gpt-4o") -> Optional[Dict[str, Optional[str]]]:
        """
        Parses a natural language date query text into a start and end datetime string.
        Example: "last week", "this month", "July 2024", "next monday to friday"
        Returns a dictionary {"start_datetime": "YYYY-MM-DD HH:MM:SS UTC", "end_datetime": "YYYY-MM-DD HH:MM:SS UTC"} 
        or None if parsing fails or query is not a range.
        Individual datetimes in the dict can be None if only one part of the range is specified (e.g. "before today").
        """
        if not self.client:
            logger.error("LLMService client not initialized. Cannot parse date range query.")
            return None

        now_utc = datetime.now(timezone.utc)
        current_time_str = now_utc.strftime("%Y-%m-%d %H:%M:%S %Z")

        prompt = f"""
        You are a precise date range parsing assistant.
        Given the current time is {current_time_str}, parse the following user input to determine a start datetime and an end datetime for a date range.
        User input: '{date_query_text}'.

        RULES:
        1.  Your entire response MUST be a JSON object.
        2.  The JSON object should have two keys: "start_datetime" and "end_datetime".
        3.  Values for these keys should be date strings in the exact format 'YYYY-MM-DD HH:MM:SS UTC'.
        4.  If the user input implies an open-ended range (e.g., "since last Monday", "until next Friday"), one of the keys can be null.
            - For "since last Monday": "start_datetime" would be last Monday 00:00:00 UTC, "end_datetime" would be null.
            - For "until next Friday": "start_datetime" would be null, "end_datetime" would be next Friday 23:59:59 UTC.
            - For "today": "start_datetime" is today 00:00:00 UTC, "end_datetime" is today 23:59:59 UTC.
            - For "last week": "start_datetime" is the beginning of last week (e.g., Monday 00:00:00 UTC), "end_datetime" is the end of last week (e.g., Sunday 23:59:59 UTC).
            - For "July 2024": "start_datetime" is "2024-07-01 00:00:00 UTC", "end_datetime" is "2024-07-31 23:59:59 UTC".
        5.  If the input is not a recognizable date range or specific date, or is too vague, respond with: {{"start_datetime": null, "end_datetime": null, "error": "ERROR_CANNOT_PARSE"}}
        6.  If the input refers to a single day (e.g. "yesterday", "May 10th"), set start_datetime to the beginning of that day (00:00:00 UTC) and end_datetime to the end of that day (23:59:59 UTC).

        Examples:
        User input: "last week" (Current time: 2024-05-20 10:00:00 UTC)
        Output: {{"start_datetime": "2024-05-13 00:00:00 UTC", "end_datetime": "2024-05-19 23:59:59 UTC"}}

        User input: "this month" (Current time: 2024-05-20 10:00:00 UTC)
        Output: {{"start_datetime": "2024-05-01 00:00:00 UTC", "end_datetime": "2024-05-31 23:59:59 UTC"}}
        
        User input: "today" (Current time: 2024-05-20 10:00:00 UTC)
        Output: {{"start_datetime": "2024-05-20 00:00:00 UTC", "end_datetime": "2024-05-20 23:59:59 UTC"}}

        User input: "since yesterday" (Current time: 2024-05-20 10:00:00 UTC)
        Output: {{"start_datetime": "2024-05-19 00:00:00 UTC", "end_datetime": null}}

        User input: "until tomorrow evening" (Current time: 2024-05-20 10:00:00 UTC)
        Output: {{"start_datetime": null, "end_datetime": "2024-05-21 23:59:59 UTC"}}
        
        User input: "gibberish"
        Output: {{"start_datetime": null, "end_datetime": null, "error": "ERROR_CANNOT_PARSE"}}
        """

        logger.info(f"Attempting to parse date range from text: '{date_query_text}' with current time context: {current_time_str}")

        try:
            raw_response_text = await self.get_completion(prompt, model=model)

            if not raw_response_text:
                logger.warning(f"LLM returned no response for date range parsing of '{date_query_text}'.")
                return None
            
            logger.debug(f"Raw LLM response for date range parsing: {raw_response_text}")

            import json
            cleaned_response_text = raw_response_text.strip()
            if cleaned_response_text.startswith("```json"):
                cleaned_response_text = cleaned_response_text[7:]
            if cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[:-3]
            cleaned_response_text = cleaned_response_text.strip()
            
            parsed_json = json.loads(cleaned_response_text)

            if not isinstance(parsed_json, dict) or ("start_datetime" not in parsed_json and "end_datetime" not in parsed_json):
                logger.error(f"LLM response for date range parsing was not a valid dictionary with expected keys. Response: {cleaned_response_text}")
                return None
            
            if parsed_json.get("error") == "ERROR_CANNOT_PARSE":
                logger.warning(f"LLM indicated it cannot parse date range: '{date_query_text}'.")
                return None

            # Validate date formats if they exist
            start_dt_str = parsed_json.get("start_datetime")
            end_dt_str = parsed_json.get("end_datetime")

            if start_dt_str:
                try:
                    datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S %Z")
                except ValueError:
                    logger.warning(f"LLM returned invalid start_datetime format: {start_dt_str}. Query: '{date_query_text}'")
                    # Decide if to return None or try to recover/ignore this part
                    parsed_json["start_datetime"] = None # Invalidate if malformed
            
            if end_dt_str:
                try:
                    datetime.strptime(end_dt_str, "%Y-%m-%d %H:%M:%S %Z")
                except ValueError:
                    logger.warning(f"LLM returned invalid end_datetime format: {end_dt_str}. Query: '{date_query_text}'")
                    parsed_json["end_datetime"] = None # Invalidate if malformed
            
            # Return the dict with potentially null start/end if one part was invalid but other was okay,
            # or if LLM intentionally returned one as null for open ranges.
            # If both are null and no error was explicitly set by LLM, it means parsing failed.
            if not parsed_json.get("start_datetime") and not parsed_json.get("end_datetime") and not parsed_json.get("error"):
                 logger.warning(f"LLM parsing for date range query '{date_query_text}' resulted in no valid start or end dates.")
                 return None


            logger.info(f"Successfully parsed date range query '{date_query_text}': {parsed_json}")
            return {"start_datetime": parsed_json.get("start_datetime"), "end_datetime": parsed_json.get("end_datetime")}

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response for date range query '{date_query_text}': {e}. Response was: {cleaned_response_text}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during date range query parsing for '{date_query_text}': {e}", exc_info=True)
            return None

# Example usage (for testing purposes, would not be here in production)
if __name__ == '__main__':
    import asyncio
    # This example assumes OPENAI_API_KEY is set in the environment or .env file
    
    async def main():
        logging.basicConfig(level=logging.INFO)
        logger.info("Starting LLMService example...")
        
        llm_service = LLMService()
        if not llm_service.client:
            logger.error("LLMService client could not be initialized. Exiting example.")
            return

        # Test embedding
        embedding_text = "Hello, world! This is a test of the embedding service."
        embedding = await llm_service.generate_embedding(embedding_text)
        if embedding:
            logger.info(f"Generated embedding (first 5 elements): {embedding[:5]}")
            logger.info(f"Embedding dimension: {len(embedding)}")
        else:
            logger.error("Failed to generate embedding.")

        # Test completion
        completion_prompt = "What is the capital of France?"
        completion = await llm_service.get_completion(completion_prompt)
        if completion:
            logger.info(f"Completion for prompt '{completion_prompt}': {completion}")
        else:
            logger.error("Failed to get completion.")
            
        # Test duration parsing (rudimentary, as it's not fully implemented)
        duration_text = "next Tuesday at 3pm"
        parsed_duration_info = await llm_service.parse_natural_language_duration(duration_text)
        if parsed_duration_info: # This will be None for now
            logger.info(f"Parsed duration for '{duration_text}': {parsed_duration_info}")
        else:
            logger.info(f"Parsing duration for '{duration_text}' returned None (as expected for placeholder).")

    asyncio.run(main()) 