import logging
from typing import List

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
    if not text:
        logger.warning("simple_chunk_text received empty or None text.")
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
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end]) # Slicing handles if end > text_len
        
        if end >= text_len:
            break # Reached the end of the text
            
        start += (chunk_size - overlap)
        
        # This check was to prevent empty last chunk, but Python slicing handles out-of-bounds gracefully.
        # if start >= text_len: 
        #     break
            
    logger.debug(f"Chunked text of length {text_len} into {len(chunks)} chunks (size: {chunk_size}, overlap: {overlap}).")
    return chunks

# TODO: Consider adding more sophisticated chunking strategies, e.g.:
# - RecursiveCharacterTextSplitter (common in Langchain)
# - Sentence-aware chunking (e.g., using NLTK or spaCy for sentence tokenization first)
# - Markdown-aware or code-aware chunking if those content types are expected. 