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


# Session schemas
class SessionBase(BaseModel):
    notes: Optional[str] = None


class SessionCreate(SessionBase):
    pass


class SessionResponse(SessionBase):
    id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[float] = None
    recording_count: int = 0

    class Config:
        from_attributes = True


class SessionEnd(BaseModel):
    notes: Optional[str] = None


# Recording schemas
class RecordingBase(BaseModel):
    clip_id: Optional[int] = None
    session_id: Optional[int] = None


class RecordingResponse(BaseModel):
    id: int
    filename: str
    clip_id: Optional[int] = None
    session_id: Optional[int] = None
    attempt_number: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecordingListResponse(BaseModel):
    recordings: List[RecordingResponse]


# Statistics schemas
class DailyStats(BaseModel):
    date: str
    recording_count: int
    session_count: int
    total_duration_minutes: float


class OverallStats(BaseModel):
    total_recordings: int
    total_sessions: int
    total_clips: int
    total_practice_minutes: float
    recordings_this_week: int
    average_recordings_per_session: float

