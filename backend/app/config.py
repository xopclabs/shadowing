import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


def _get_data_dir() -> Path:
    """Get data directory from environment or use default."""
    env_dir = os.environ.get('DATA_DIR')
    if env_dir:
        return Path(env_dir)
    # Default: project_root/data
    return Path(__file__).parent.parent.parent / 'data'


class Settings(BaseSettings):
    # Base paths
    project_root: Path = Path(__file__).parent.parent.parent
    data_dir: Path = _get_data_dir()
    recordings_dir: Path = Path(os.environ.get('RECORDINGS_DIR', '')) or data_dir / 'recordings'
    clips_dir: Path = Path(os.environ.get('CLIPS_DIR', '')) or data_dir / 'clips'

    # Database - use absolute path based on data_dir
    @property
    def database_url(self) -> str:
        db_path = self.data_dir / 'shadowing.db'
        return f'sqlite+aiosqlite:///{db_path}'

    # CORS - allow all origins in development
    cors_origins: List[str] = ['*']

    # API settings
    api_prefix: str = '/api'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.clips_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()

