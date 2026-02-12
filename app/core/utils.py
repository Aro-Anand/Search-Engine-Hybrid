import re
import unicodedata

def generate_slug(text: str) -> str:
    """
    Generate a URL-friendly slug from a string.
    
    Example:
    "Pizza Hut & Cafe!" -> "pizza-hut-cafe"
    """
    if not text:
        return ""
        
    # Standardize to lowercase
    text = text.lower()
    
    # Normalize unicode characters (e.g., remove accents)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    
    # Replace non-alphanumeric characters with spaces
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    
    # Replace whitespace and hyphens with a single hyphen
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    
    return text
