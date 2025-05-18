import logging
from typing import List
import re

logger = logging.getLogger(__name__)

def simple_chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Rudimentary text chunker.
    Splits text into chunks of a specified size with a given overlap between chunks.

    Args:
        text: The text content to chunk.
        chunk_size: The desired maximum size of each chunk.
        overlap: The number of characters to overlap between consecutive chunks.

    Returns:
        A list of text chunks.
    """
    if not text or not isinstance(text, str):
        return []
    
    if chunk_size <= 0:
        logger.error(f"Invalid chunk_size: {chunk_size}. Must be positive.")
        # Or raise ValueError("chunk_size must be positive")
        return [text] # Or handle error differently
        
    if overlap < 0 or overlap >= chunk_size:
        logger.warning(f"Invalid overlap: {overlap}. Setting to 0. Overlap should be 0 <= overlap < chunk_size.")
        overlap = 0

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += (chunk_size - overlap)
        # Ensure start doesn't go beyond text length in case of very small text or large overlap
        if start >= len(text) and chunks:
            # This condition might occur if overlap is too large relative to chunk_size and text length
            # or if the last chunk was exactly up to len(text). Avoid adding an empty or negative slice.
            break 
    return chunks

# TODO: Consider adding more sophisticated chunking strategies, e.g.:
# - RecursiveCharacterTextSplitter (common in Langchain)
# - Sentence-aware chunking (e.g., using NLTK or spaCy for sentence tokenization first)
# - Markdown-aware or code-aware chunking if those content types are expected. 