from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# Video schemas
class VideoBase(BaseModel):
    path: str
    title: Optional[str] = None


class VideoCreate(VideoBase):
    pass


class VideoResponse(VideoBase):
    id: int
    duration: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Clip schemas
class ClipBase(BaseModel):
    start_time: float = Field(..., ge=0)
    end_time: float = Field(..., gt=0)
    transcript: Optional[str] = None


class ClipCreate(ClipBase):
    video_path: str


class ClipResponse(ClipBase):
    id: int
    video_id: int
    audio_path: str
    duration: float
    created_at: datetime

    class Config:
        from_attributes = True


class ClipExtractRequest(BaseModel):
    video_path: str = Field(..., description='Full path to the video file')
    start_time: float = Field(..., ge=0, description='Start time in seconds')
    end_time: float = Field(..., gt=0, description='End time in seconds')


# Recording schemas
class RecordingBase(BaseModel):
    clip_id: Optional[int] = None


class RecordingResponse(BaseModel):
    id: int
    filename: str
    clip_id: Optional[int] = None
    attempt_number: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecordingListResponse(BaseModel):
    recordings: List[RecordingResponse]


# Recent files schemas
class RecentFileResponse(BaseModel):
    id: int
    video_path: str
    filename: str
    last_timestamp: float
    last_used: datetime
    source: str = 'media'  # 'media' or 'youtube'
    thumbnail_url: Optional[str] = None  # For YouTube videos

    class Config:
        from_attributes = True


class RecentFileCreate(BaseModel):
    video_path: str
    last_timestamp: float = 0
    source: str = 'media'  # 'media' or 'youtube'
    thumbnail_url: Optional[str] = None  # For YouTube videos


class RecentFileListResponse(BaseModel):
    recent_files: List[RecentFileResponse]


# Statistics schemas
class OverallStats(BaseModel):
    total_recordings: int
    total_clips_practiced: int  # Clips that have at least 1 recording
    total_practice_minutes: float
    recordings_this_week: int
    first_recording_date: Optional[datetime] = None
    last_recording_date: Optional[datetime] = None


# Storage info schemas
class StorageInfo(BaseModel):
    clips_count: int
    clips_size_bytes: int
    recordings_count: int
    recordings_size_bytes: int
    total_size_bytes: int


class DeleteFilesRequest(BaseModel):
    delete_clips: bool = False
    delete_recordings: bool = False


# YouTube download schemas
class YouTubeDownloadResponse(BaseModel):
    id: int
    video_id: str
    title: str
    file_path: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    uploader: Optional[str] = None
    is_audio_only: bool
    created_at: datetime

    class Config:
        from_attributes = True


class YouTubeDownloadListResponse(BaseModel):
    downloads: List[YouTubeDownloadResponse]
