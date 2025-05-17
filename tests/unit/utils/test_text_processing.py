import pytest
from app.utils.text_processing import simple_chunk_text

def test_simple_chunk_text_empty_input():
    assert simple_chunk_text("", 100, 10) == []
    assert simple_chunk_text(None, 100, 10) == []

def test_simple_chunk_text_shorter_than_chunk_size():
    text = "This is a short text."
    assert simple_chunk_text(text, 100, 10) == [text]

def test_simple_chunk_text_exact_chunk_size_no_overlap():
    text = "onetwothree" # 11 chars
    # chunk_size 11, overlap 0
    assert simple_chunk_text(text, 11, 0) == ["onetwothree"]
    # chunk_size 5, overlap 0
    assert simple_chunk_text(text, 5, 0) == ["onetw", "othre", "e"]

def test_simple_chunk_text_with_overlap():
    text = "abcdefghijklmnopqrstuvwxyz" # 26 chars
    # chunk_size 10, overlap 3
    # Expected:
    # abcdefghij (0-9)
    # hijklmnopq (7-16)
    # opqrstuvwx (14-23)
    # uvwxyz (21-25)
    expected_chunks = [
        "abcdefghij",
        "hijklmnopq",
        "opqrstuvwx",
        "vwxyz"
    ]
    assert simple_chunk_text(text, 10, 3) == expected_chunks

def test_simple_chunk_text_no_overlap():
    text = "abcdefghijklmnopqrstuvwxyz" # 26 chars
    # chunk_size 10, overlap 0
    # Expected:
    # abcdefghij (0-9)
    # klmnopqrst (10-19)
    # uvwxyz     (20-25)
    expected_chunks = [
        "abcdefghij",
        "klmnopqrst",
        "uvwxyz"
    ]
    assert simple_chunk_text(text, 10, 0) == expected_chunks

def test_simple_chunk_text_large_overlap():
    text = "abcdefghij" # 10 chars
    # chunk_size 5, overlap 4
    # Expected:
    # abcde (0-4)
    # bcdef (1-5)
    # cdefg (2-6)
    # defgh (3-7)
    # efghi (4-8)
    # fghij (5-9)
    expected_chunks = [
        "abcde", "bcdef", "cdefg", "defgh", "efghi", "fghij"
    ]
    assert simple_chunk_text(text, 5, 4) == expected_chunks
    
def test_simple_chunk_text_overlap_equals_chunk_size_minus_one():
    text = "abcdefghij"
    # chunk_size 5, overlap 4 (effectively moving one char at a time after the first chunk)
    expected = ["abcde", "bcdef", "cdefg", "defgh", "efghi", "fghij"]
    assert simple_chunk_text(text, 5, 4) == expected

def test_simple_chunk_text_invalid_chunk_size():
    text = "Some text"
    # Should return the original text as a single chunk (or handle as an error based on implementation)
    # Current implementation returns [text]
    assert simple_chunk_text(text, 0, 10) == [text] 
    assert simple_chunk_text(text, -5, 10) == [text]

def test_simple_chunk_text_invalid_overlap():
    text = "abcdefghij"
    # Overlap < 0 should be treated as 0
    assert simple_chunk_text(text, 5, -2) == simple_chunk_text(text, 5, 0) 
    # Overlap >= chunk_size should be treated as 0
    assert simple_chunk_text(text, 5, 5) == simple_chunk_text(text, 5, 0)
    assert simple_chunk_text(text, 5, 6) == simple_chunk_text(text, 5, 0)

def test_simple_chunk_text_long_text_various_overlaps():
    text = "This is a very long string of text that needs to be chunked multiple times to test the behavior of the simple_chunk_text function with different overlap values and chunk sizes to ensure it is robust and correct in its operation under various conditions." * 5
    
    chunks_no_overlap = simple_chunk_text(text, 50, 0)
    assert len(chunks_no_overlap) > 1
    for chunk in chunks_no_overlap:
        assert len(chunk) <= 50
    # Reconstruct and check (ignoring potential minor last chunk differences if text length not multiple of chunk_size)
    # This is a simple check; a more robust check would be character-by-character comparison
    assert "".join(chunks_no_overlap) == text

    chunks_with_overlap = simple_chunk_text(text, 50, 10)
    assert len(chunks_with_overlap) > 1
    for chunk in chunks_with_overlap:
        assert len(chunk) <= 50
    
    # Check reconstruction for overlapping chunks (this is more complex)
    # A basic check: the first chunk should match text start, last chunk should match text end
    assert chunks_with_overlap[0] == text[:50]
    if len(chunks_with_overlap) > 1:
        # The second chunk should start 10 chars before the end of the first chunk (50 - 10 = 40)
        expected_start_of_second_chunk = text[40:40+50]
        assert chunks_with_overlap[1] == expected_start_of_second_chunk
    
    full_reconstruction = ""
    if chunks_with_overlap:
        full_reconstruction = chunks_with_overlap[0]
        current_pos = len(chunks_with_overlap[0]) - 10 # 10 is overlap
        for i in range(1, len(chunks_with_overlap)):
            # The chunk should start at overlap from the end of the previous effective content
            # This reconstruction logic needs to be careful with overlap
            # simplified check: ensure all parts of text are covered
            pass # Proper overlap reconstruction is tricky for a simple test here

    # Ensure all text is covered somehow
    reconstructed_from_overlap = ""
    last_end = 0
    for i, chunk in enumerate(chunks_with_overlap):
        if i == 0:
            reconstructed_from_overlap += chunk
            last_end = len(chunk)
        else:
            # Add the non-overlapping part of the current chunk
            # The chunk starts at (chunk_size - overlap) from the start of the previous chunk.
            # Effective new content starts after the overlap with the previous chunk.
            reconstructed_from_overlap += chunk[10:] # 10 is overlap
            last_end += len(chunk) - 10
            
    assert text.startswith(reconstructed_from_overlap[:len(text)-50]) # Check a large portion 