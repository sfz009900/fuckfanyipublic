"""
Text processing utilities for OCR and translation.
"""


def clean_text(text):
    """
    Clean and normalize detected text.
    
    Args:
        text (str): The text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = " ".join(text.split())
    
    # Remove common OCR artifacts
    text = text.replace("|", "I")  # Common OCR mistake
    text = text.replace("1", "l")  # Another common mistake
    
    # Remove non-printable characters
    text = "".join(char for char in text if char.isprintable())
    
    # Normalize quotes and apostrophes
    text = text.replace(""", '"').replace(""", '"')
    text = text.replace("'", "'").replace("'", "'")
    
    return text.strip() 