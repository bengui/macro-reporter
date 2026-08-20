"""API key management utilities for macro_reporter."""

import os
from pathlib import Path

API_KEYS_DIR = Path(__file__).parent.parent.parent / "api_keys"


def load_api_keys() -> dict[str, str]:
    """
    Load all API keys from the api_keys directory.
    
    Each key should be in a separate .txt file named after the service.
    Example: api_keys/FRED.txt should contain the FRED API key.
    
    Returns:
        Dictionary mapping service names (uppercase) to API keys.
    """
    keys = {}
    
    if not API_KEYS_DIR.exists():
        return keys
    
    for key_file in API_KEYS_DIR.glob("*.txt"):
        service_name = key_file.stem.upper()
        try:
            with open(key_file, "r") as f:
                key = f.read().strip()
                if key:
                    keys[service_name] = key
        except Exception:
            pass
    
    return keys


def get_api_key(service: str) -> str | None:
    """
    Get API key for a specific service.
    
    Args:
        service: Service name (case-insensitive)
    
    Returns:
        API key if found, None otherwise.
    """
    keys = load_api_keys()
    return keys.get(service.upper())


def set_api_key(service: str, key: str) -> bool:
    """
    Save an API key to the api_keys directory.
    
    Args:
        service: Service name (will be saved as UPPERCASE.txt)
        key: API key value
    
    Returns:
        True if saved successfully, False otherwise.
    """
    API_KEYS_DIR.mkdir(parents=True, exist_ok=True)
    key_file = API_KEYS_DIR / f"{service.upper()}.txt"
    
    try:
        with open(key_file, "w") as f:
            f.write(key.strip())
        # Set file permissions to 600 (owner read/write only)
        os.chmod(key_file, 0o600)
        return True
    except Exception:
        return False
