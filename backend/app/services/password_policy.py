import string
import secrets

def generate_sequential_password(prefix: str, index: int, padding: int = 3) -> str:
    """Generate a password with a prefix and a padded sequential number."""
    number_str = str(index).zfill(padding)
    return f"{prefix}{number_str}"

def generate_random_password(length: int = 12) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for i in range(length))
