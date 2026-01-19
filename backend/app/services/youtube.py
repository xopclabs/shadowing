import asyncio
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from app.services.settings import settings_service


class VideoInfo(BaseModel):
    """Information about a YouTube video."""
    id: str
    title: str
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    uploader: Optional[str] = None
    description: Optional[str] = None


class DownloadResult(BaseModel):
    """Result of a download operation."""
    success: bool
    video_id: str
    title: str
    file_path: Optional[str] = None
    error: Optional[str] = None


class YouTubeDownloadError(Exception):
    """Raised when a YouTube download fails."""
    pass


class YouTubeService:
    """Service for downloading videos from YouTube using yt-dlp."""

    def _get_proxy_args(self) -> list:
        """Get proxy arguments for yt-dlp if configured."""
        settings = settings_service.get_settings()
        if settings.socks5_proxy:
            return ['--proxy', settings.socks5_proxy]
        return []

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize a title to be safe for filenames."""
        # Remove or replace problematic characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
        sanitized = sanitized.strip()
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        return sanitized or 'video'

    async def get_video_info(self, url: str) -> VideoInfo:
        """
        Get information about a YouTube video without downloading.

        Args:
            url: YouTube video URL

        Returns:
            VideoInfo with video metadata

        Raises:
            YouTubeDownloadError: If info extraction fails
        """
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-download',
            '--no-warnings',
            *self._get_proxy_args(),
            url,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else 'Unknown error'
                raise YouTubeDownloadError(f'Failed to get video info: {error_msg}')

            import json
            data = json.loads(stdout.decode())

            return VideoInfo(
                id=data.get('id', ''),
                title=data.get('title', 'Unknown'),
                duration=data.get('duration'),
                thumbnail=data.get('thumbnail'),
                uploader=data.get('uploader'),
                description=data.get('description'),
            )

        except FileNotFoundError:
            raise YouTubeDownloadError(
                'yt-dlp not found. Please ensure yt-dlp is installed.'
            )
        except Exception as e:
            if isinstance(e, YouTubeDownloadError):
                raise
            raise YouTubeDownloadError(f'Failed to get video info: {str(e)}')

    async def download_video(
        self,
        url: str,
        audio_only: bool = False,
    ) -> DownloadResult:
        """
        Download a YouTube video.

        Args:
            url: YouTube video URL
            audio_only: If True, download only audio (mp3)

        Returns:
            DownloadResult with download status and file path

        Raises:
            YouTubeDownloadError: If download fails
        """
        download_dir = settings_service.get_youtube_download_dir()

        # Get video info first to construct filename
        try:
            info = await self.get_video_info(url)
        except YouTubeDownloadError as e:
            return DownloadResult(
                success=False,
                video_id='',
                title='Unknown',
                error=str(e),
            )

        # Construct output template
        safe_title = self._sanitize_filename(info.title)
        output_template = str(download_dir / f'{safe_title}_%(id)s.%(ext)s')

        # Build yt-dlp command
        cmd = [
            'yt-dlp',
            '--no-warnings',
            '-o', output_template,
            *self._get_proxy_args(),
        ]

        if audio_only:
            cmd.extend([
                '-x',  # Extract audio
                '--audio-format', 'mp3',
                '--audio-quality', '192K',
            ])
        else:
            # Download best quality video+audio
            cmd.extend([
                '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '--merge-output-format', 'mp4',
            ])

        cmd.append(url)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else 'Unknown error'
                return DownloadResult(
                    success=False,
                    video_id=info.id,
                    title=info.title,
                    error=f'Download failed: {error_msg}',
                )

            # Find the downloaded file
            ext = 'mp3' if audio_only else 'mp4'
            expected_filename = f'{safe_title}_{info.id}.{ext}'
            file_path = download_dir / expected_filename

            # If exact file doesn't exist, try to find it
            if not file_path.exists():
                # Look for any file with the video ID
                matching_files = list(download_dir.glob(f'*{info.id}*'))
                if matching_files:
                    file_path = matching_files[0]
                else:
                    return DownloadResult(
                        success=False,
                        video_id=info.id,
                        title=info.title,
                        error='Download completed but file not found',
                    )

            return DownloadResult(
                success=True,
                video_id=info.id,
                title=info.title,
                file_path=str(file_path),
            )

        except FileNotFoundError:
            raise YouTubeDownloadError(
                'yt-dlp not found. Please ensure yt-dlp is installed.'
            )
        except Exception as e:
            if isinstance(e, YouTubeDownloadError):
                raise
            return DownloadResult(
                success=False,
                video_id=info.id,
                title=info.title,
                error=f'Download failed: {str(e)}',
            )


# Singleton instance
youtube_service = YouTubeService()

