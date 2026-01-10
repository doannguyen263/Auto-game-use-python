"""
Text utilities - Vietnamese text processing
"""
import unicodedata
import re


def remove_accents(text: str) -> str:
    """
    Remove Vietnamese accents from text
    
    Args:
        text: Text with Vietnamese accents
    
    Returns:
        Text without accents
    """
    if not text:
        return text
    
    # Normalize to NFD (decomposed form)
    nfd = unicodedata.normalize('NFD', text)
    
    # Remove combining diacritical marks
    no_accents = ''.join(
        char for char in nfd
        if unicodedata.category(char) != 'Mn'
    )
    
    # Normalize to NFC (composed form) to ensure consistency
    return unicodedata.normalize('NFC', no_accents)


def sanitize_filename(text: str) -> str:
    """
    Sanitize text for use as filename/directory name
    
    Args:
        text: Text to sanitize
    
    Returns:
        Sanitized text safe for filesystem
    """
    if not text:
        return text
    
    # Remove accents
    text = remove_accents(text)
    
    # Replace spaces with underscores
    text = text.replace(' ', '_')
    
    # Remove special characters except underscore and hyphen
    text = re.sub(r'[^\w\-_]', '', text)
    
    # Remove multiple consecutive underscores
    text = re.sub(r'_+', '_', text)
    
    # Remove leading/trailing underscores
    text = text.strip('_')
    
    return text

