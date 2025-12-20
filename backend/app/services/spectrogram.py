import asyncio
import struct
import zlib
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray



class SpectrogramError(Exception):
    """Raised when spectrogram generation fails."""
    pass


class SpectrogramService:
    """
    Service for generating spectrograms that match the frontend JS implementation.
    
    Uses the exact same color scheme and parameters as the frontend
    Spectrogram.vue component.
    """
    
    # Configuration matching frontend
    FFT_SIZE = 1024
    HOP_SIZE = 256
    MAX_WIDTH = 800
    MAX_HEIGHT = 200
    
    # Background color (matches frontend BG_COLOR)
    BG_COLOR = (10, 0, 30)
    
    def _hann_window(self, size: int) -> NDArray[np.float32]:
        """Generate Hann window matching frontend implementation."""
        return 0.5 * (1 - np.cos(2 * np.pi * np.arange(size) / (size - 1)))
    
    def _get_color_for_value(self, value: float) -> Tuple[int, int, int]:
        """
        Convert normalized magnitude to RGB color.
        Matches frontend getColorForValue exactly.
        """
        v = value ** 0.7
        
        if v < 0.25:
            t = v / 0.25
            return (
                int(10 + 50 * t),
                int(10 * t),
                int(30 + 70 * t),
            )
        elif v < 0.5:
            t = (v - 0.25) / 0.25
            return (
                int(60 + 140 * t),
                int(10 + 30 * t),
                int(100 + 50 * t),
            )
        elif v < 0.75:
            t = (v - 0.5) / 0.25
            return (
                int(200 + 55 * t),
                int(40 + 100 * t),
                int(150 - 100 * t),
            )
        else:
            t = (v - 0.75) / 0.25
            return (
                255,
                int(140 + 115 * t),
                int(50 + 150 * t),
            )
    
    async def _decode_audio(self, audio_path: str) -> Tuple[NDArray[np.float32], int]:
        """
        Decode audio file to raw PCM samples using FFmpeg.
        
        Returns:
            Tuple of (samples as float32 array, sample_rate)
        """
        cmd = [
            'ffmpeg',
            '-i', audio_path,
            '-f', 's16le',  # Raw 16-bit signed little-endian PCM
            '-ac', '1',     # Mono
            '-ar', '44100', # 44.1kHz
            '-v', 'error',
            'pipe:1',       # Output to stdout
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else 'Unknown FFmpeg error'
                raise SpectrogramError(f'FFmpeg failed: {error_msg}')
            
            # Convert bytes to numpy array
            samples = np.frombuffer(stdout, dtype=np.int16).astype(np.float32)
            # Normalize to [-1, 1]
            samples = samples / 32768.0
            
            return samples, 44100
            
        except FileNotFoundError:
            raise SpectrogramError('FFmpeg not found')
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds."""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path,
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
            return 0.0
            
        except (FileNotFoundError, ValueError):
            return 0.0
    
    def _compute_spectrogram(
        self,
        samples: NDArray[np.float32],
        max_duration: Optional[float] = None,
        duration: float = 0.0,
    ) -> NDArray[np.uint8]:
        """
        Compute spectrogram and return as RGB image array.
        
        Args:
            samples: Audio samples as float32 array
            max_duration: If provided, scale spectrogram width to this duration
            duration: Actual duration of this audio
            
        Returns:
            RGB image as uint8 array of shape (height, width, 3)
        """
        num_frames = max(1, (len(samples) - self.FFT_SIZE) // self.HOP_SIZE + 1)
        num_bins = self.FFT_SIZE // 2
        
        # Calculate dimensions matching frontend
        duration_ratio = duration / max_duration if max_duration and max_duration > 0 else 1.0
        base_width = min(num_frames, self.MAX_WIDTH)
        display_width = base_width
        spectrogram_width = max(1, int(base_width * duration_ratio))
        display_height = min(num_bins, self.MAX_HEIGHT)
        
        # Prepare window function
        window = self._hann_window(self.FFT_SIZE)
        
        # Compute magnitudes
        frame_step = max(1, num_frames // spectrogram_width)
        magnitudes = []
        max_magnitude = -np.inf
        
        for frame_idx in range(0, num_frames, frame_step):
            start_sample = frame_idx * self.HOP_SIZE
            end_sample = start_sample + self.FFT_SIZE
            
            # Extract and window the frame
            if end_sample <= len(samples):
                frame = samples[start_sample:end_sample] * window
            else:
                # Pad with zeros
                frame = np.zeros(self.FFT_SIZE, dtype=np.float32)
                available = len(samples) - start_sample
                if available > 0:
                    frame[:available] = samples[start_sample:] * window[:available]
            
            # Compute FFT
            fft_result = np.fft.rfft(frame)
            
            # Compute magnitude in dB
            use_bins = min(num_bins, display_height * 2)
            magnitude = np.abs(fft_result[:use_bins])
            db = 20 * np.log10(magnitude + 1e-10)
            
            magnitudes.append(db)
            frame_max = np.max(db)
            if frame_max > max_magnitude:
                max_magnitude = frame_max
        
        # Normalize and create image
        min_db = max_magnitude - 80
        
        # Initialize image with background color
        image = np.zeros((display_height, display_width, 3), dtype=np.uint8)
        image[:, :, 0] = self.BG_COLOR[0]
        image[:, :, 1] = self.BG_COLOR[1]
        image[:, :, 2] = self.BG_COLOR[2]
        
        # Fill in spectrogram data
        actual_cols = min(len(magnitudes), spectrogram_width)
        
        for col in range(actual_cols):
            frame_mags = magnitudes[col]
            
            for row in range(display_height):
                bin_idx = int((display_height - 1 - row) * (len(frame_mags) / display_height))
                bin_idx = min(bin_idx, len(frame_mags) - 1)
                
                db = frame_mags[bin_idx]
                normalized = max(0.0, min(1.0, (db - min_db) / (max_magnitude - min_db + 1e-10)))
                
                r, g, b = self._get_color_for_value(normalized)
                image[row, col, 0] = r
                image[row, col, 1] = g
                image[row, col, 2] = b
        
        return image
    
    def _encode_png(self, image: NDArray[np.uint8]) -> bytes:
        """
        Encode RGB image array to PNG bytes.
        
        Simple PNG encoder without external dependencies.
        """
        height, width, _ = image.shape
        
        def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
            chunk_len = struct.pack('>I', len(data))
            chunk_crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
            return chunk_len + chunk_type + data + chunk_crc
        
        # PNG signature
        signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk
        ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        ihdr = png_chunk(b'IHDR', ihdr_data)
        
        # IDAT chunk (image data)
        raw_data = b''
        for row in range(height):
            raw_data += b'\x00'  # Filter type: None
            raw_data += image[row].tobytes()
        
        compressed = zlib.compress(raw_data, 9)
        idat = png_chunk(b'IDAT', compressed)
        
        # IEND chunk
        iend = png_chunk(b'IEND', b'')
        
        return signature + ihdr + idat + iend
    
    async def generate_spectrogram_png(
        self,
        audio_path: str,
        max_duration: Optional[float] = None,
    ) -> Tuple[bytes, float]:
        """
        Generate spectrogram PNG for an audio file.
        
        Args:
            audio_path: Path to the audio file
            max_duration: Optional max duration for scaling
            
        Returns:
            Tuple of (PNG bytes, audio duration in seconds)
        """
        path = Path(audio_path)
        if not path.exists():
            raise SpectrogramError(f'Audio file not found: {audio_path}')
        
        # Decode audio
        samples, sample_rate = await self._decode_audio(str(path))
        duration = len(samples) / sample_rate
        
        # Compute spectrogram
        image = self._compute_spectrogram(samples, max_duration, duration)
        
        # Encode to PNG
        png_bytes = self._encode_png(image)
        
        return png_bytes, duration


# Singleton instance
spectrogram_service = SpectrogramService()

