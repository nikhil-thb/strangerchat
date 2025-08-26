from better_profanity import profanity
import re

# Initialize profanity filter
profanity.load_censor_words()

# Add custom bad words or patterns
CUSTOM_BAD_WORDS = [
    # Add your custom bad words here
]

for word in CUSTOM_BAD_WORDS:
    profanity.add_censor_word(word)

def is_nsfw(text):
    """
    Check if the given text contains NSFW content
    Returns True if NSFW content detected, False otherwise
    """
    # Check using better-profanity
    if profanity.contains_profanity(text):
        return True
    
    # Add additional checks here if needed
    return False