
import secrets
import string


def generate_assistant_id(prefix: str = "asst_", length: int = 24) -> str:
    """
    Generate a unique ID like 'asst_jRgR5t2U7o8nUPkNGv5HWOgV'.

    - prefix: leading string (defaults to 'asst_')
    - length: number of random characters after the prefix
    """
    # URL-safe characters similar to what OpenAI-style IDs use
    alphabet = string.ascii_letters + string.digits  # a-zA-Z0-9

    # cryptographically strong randomness
    random_part = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}{random_part}"
