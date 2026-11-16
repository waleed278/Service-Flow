
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

EXPECTED_API_KEY = os.getenv("INTERNAL_API_KEY")

if not EXPECTED_API_KEY or len(EXPECTED_API_KEY) < 32:
    raise RuntimeError(
        "INTERNAL_API_KEY must be configured securely"
    )

api_key_scheme = APIKeyHeader(
    name="X-Internal-API-Key",
    auto_error=False
)

def require_internal_api_key(
    provided_key: str | None = Depends(api_key_scheme)
) -> None:

    valid = (
        provided_key is not None
        and secrets.compare_digest(
            provided_key,
            EXPECTED_API_KEY
        )
    )

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "APIKey"}
        )