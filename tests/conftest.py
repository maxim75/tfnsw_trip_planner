"""Pytest configuration shared across the test suite.

Loads variables from a local ``.env`` file (e.g. ``TFNSW_API_KEY``) so the live
integration tests can pick up your API key without exporting it manually. This
is a no-op if ``python-dotenv`` isn't installed or no ``.env`` file exists.
"""
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is an optional dev convenience
    load_dotenv = None

if load_dotenv is not None:
    # Look for a .env at the repo root (one level above tests/).
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)
