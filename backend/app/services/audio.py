import asyncio
import subprocess
import uuid
from pathlib import Path
from typing import Optional, Tuple

from app.config import settings


class AudioExtractionError(Exception):
    """Raised when audio extraction fails."""
    pass


class AudioService:
    """Service for audio/video processing using FFmpeg."""

    def __init__(self):
        self.clips_dir = settings.clips_dir

    async def extract_audio_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        output_format: str = 'mp3',
    ) -> Tuple[str, Path]:
        """
        Extract an audio clip from a video file.
        
        Args:
            video_path: Path to the source video file
            start_time: Start time in seconds
            end_time: End time in seconds
            output_format: Output audio format (mp3, wav, ogg)
            
        Returns:
            Tuple of (clip_id, output_path)
            
        Raises:
            AudioExtractionError: If extraction fails
        """
        # Validate input file exists
        input_path = Path(video_path)
        if not input_path.exists():
            raise AudioExtractionError(f'Video file not found: {video_path}')

        # Generate unique clip ID and output path
        clip_id = str(uuid.uuid4())
        duration = end_time - start_time
        
        # Create descriptive filename
        timestamp = f'{int(start_time)}-{int(end_time)}'
        filename = f'{input_path.stem}_{timestamp}_{clip_id[:8]}.{output_format}'
        output_path = self.clips_dir / filename

        # Build FFmpeg command
        # Using hybrid seeking: fast seek to ~10s before start, then accurate seek
        # This gives both speed and millisecond precision
        fast_seek = max(0, start_time - 10)  # Seek to 10s before for safety margin
        accurate_seek = start_time - fast_seek  # Remaining time for accurate seek
        
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if exists
            '-ss', str(fast_seek),  # Fast seek to approximate position (before -i)
            '-i', str(input_path),  # Input file
            '-ss', str(accurate_seek),  # Accurate seek from there (after -i)
            '-t', str(duration),  # Duration
            '-vn',  # No video
            '-acodec', self._get_codec(output_format),
            '-ar', '44100',  # Sample rate
            '-ac', '2',  # Stereo
            '-b:a', '192k',  # Bitrate
            str(output_path),
        ]

        try:
            # Run FFmpeg asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else 'Unknown FFmpeg error'
                raise AudioExtractionError(f'FFmpeg failed: {error_msg}')

            if not output_path.exists():
                raise AudioExtractionError('Output file was not created')

            return clip_id, output_path

        except FileNotFoundError:
            raise AudioExtractionError(
                'FFmpeg not found. Please ensure FFmpeg is installed.'
            )
        except Exception as e:
            if isinstance(e, AudioExtractionError):
                raise
            raise AudioExtractionError(f'Extraction failed: {str(e)}')

    def _get_codec(self, format: str) -> str:
        """Get the appropriate codec for the output format."""
        codecs = {
            'mp3': 'libmp3lame',
            'wav': 'pcm_s16le',
            'ogg': 'libvorbis',
            'aac': 'aac',
            'm4a': 'aac',
        }
        return codecs.get(format, 'libmp3lame')

    async def get_video_duration(self, video_path: str) -> Optional[float]:
        """
        Get the duration of a video file in seconds.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Duration in seconds, or None if it cannot be determined
        """
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, _ = await process.communicate()

            if process.returncode == 0 and stdout:
                return float(stdout.decode().strip())
            return None

        except (FileNotFoundError, ValueError):
            return None

    def get_clip_path(self, filename: str) -> Optional[Path]:
        """Get the full path to a clip file if it exists."""
        clip_path = self.clips_dir / filename
        return clip_path if clip_path.exists() else None


# Singleton instance
audio_service = AudioService()
