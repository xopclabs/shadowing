import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from app.config import settings as app_settings


class ServerSettings(BaseModel):
    """Server-side configurable settings stored in JSON file."""
    socks5_proxy: Optional[str] = None
    youtube_download_dir: Optional[str] = None


class SettingsService:
    """Service for managing server-side settings stored in a JSON file."""

    def __init__(self):
        self.settings_file = app_settings.data_dir / 'server_settings.json'
        self._settings: Optional[ServerSettings] = None

    def _ensure_file_exists(self) -> None:
        """Create settings file with defaults if it doesn't exist."""
        if not self.settings_file.exists():
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            self._save(ServerSettings())

    def _load(self) -> ServerSettings:
        """Load settings from JSON file."""
        self._ensure_file_exists()
        try:
            with open(self.settings_file, 'r') as f:
                data = json.load(f)
                return ServerSettings(**data)
        except (json.JSONDecodeError, ValueError):
            # If file is corrupted, reset to defaults
            default_settings = ServerSettings()
            self._save(default_settings)
            return default_settings

    def _save(self, settings: ServerSettings) -> None:
        """Save settings to JSON file."""
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_file, 'w') as f:
            json.dump(settings.model_dump(), f, indent=2)
        self._settings = settings

    def get_settings(self) -> ServerSettings:
        """Get current server settings."""
        if self._settings is None:
            self._settings = self._load()
        return self._settings

    def update_settings(
        self,
        socks5_proxy: Optional[str] = None,
        youtube_download_dir: Optional[str] = None,
    ) -> ServerSettings:
        """Update server settings with provided values."""
        current = self.get_settings()

        # Update only provided values (None means "don't change", empty string means "clear")
        if socks5_proxy is not None:
            current.socks5_proxy = socks5_proxy if socks5_proxy else None
        if youtube_download_dir is not None:
            current.youtube_download_dir = youtube_download_dir if youtube_download_dir else None

        self._save(current)
        return current

    def get_youtube_download_dir(self) -> Path:
        """Get the YouTube download directory, creating it if needed."""
        settings = self.get_settings()
        if settings.youtube_download_dir:
            download_dir = Path(settings.youtube_download_dir)
        else:
            # Default to data_dir/youtube
            download_dir = app_settings.data_dir / 'youtube'

        download_dir.mkdir(parents=True, exist_ok=True)
        return download_dir


# Singleton instance
settings_service = SettingsService()

