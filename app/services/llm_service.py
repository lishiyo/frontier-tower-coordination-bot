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