from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.settings import settings_service, ServerSettings


router = APIRouter()


class SettingsUpdateRequest(BaseModel):
    """Request to update server settings."""
    socks5_proxy: Optional[str] = None
    youtube_download_dir: Optional[str] = None


@router.get('/settings', response_model=ServerSettings)
async def get_settings():
    """Get current server settings."""
    return settings_service.get_settings()


@router.post('/settings', response_model=ServerSettings)
async def update_settings(request: SettingsUpdateRequest):
    """Update server settings."""
    return settings_service.update_settings(
        socks5_proxy=request.socks5_proxy,
        youtube_download_dir=request.youtube_download_dir,
    )

