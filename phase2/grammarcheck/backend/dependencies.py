from fastapi import Header, HTTPException

from config import settings


async def verify_api_key(x_api_key: str | None = Header(None)):
    if not settings.enable_api_key:
        return True
    if not settings.api_key:
        return True
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True
