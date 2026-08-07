"""Generate a random Flask SECRET_KEY.

Usage::

    python scripts/generate_secret.py
"""

import secrets

print(secrets.token_hex(32))
