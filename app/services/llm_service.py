import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI # Using AsyncOpenAI for non-blocking calls
from app.config import ConfigService

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

    async def parse_natural_language_duration(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parses natural language text to extract a duration or a specific deadline date.
        Example: "7 days", "for 3 weeks", "until May 21st at 5 PM"
        Returns a dictionary representing the duration (e.g., {"days": 7}) or deadline, 
        or None if parsing fails.
        This will require a carefully crafted prompt.
        """
        if not self.client:
            logger.error("LLMService client not initialized. Cannot parse duration.")
            return None
        
        # Placeholder for actual implementation
        logger.info(f"Attempting to parse duration from text: '{text}'")
        # TODO: Implement LLM call to parse duration.
        # This is a complex task and might involve:
        # 1. Crafting a prompt that asks the LLM to convert text to a structured date/duration.
        # 2. Defining a function call or expecting JSON output for easy parsing.
        # 3. Handling various date/time formats and relative durations.
        
        # Example of what the LLM might be guided to return (simplified):
        # For "7 days from now": {"type": "relative", "days": 7}
        # For "until May 21st 2024 at 5 PM": {"type": "absolute", "year": 2024, "month": 5, "day": 21, "hour": 17, "minute": 0}
        
        # For now, returning None as it's not implemented.
        await self.get_completion(f"Parse this duration: {text}") # Dummy call to test client
        logger.warning("parse_natural_language_duration is not fully implemented yet.")
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