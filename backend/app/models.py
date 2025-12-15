from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Video(Base):
    """Represents a source video file."""
    __tablename__ = 'videos'

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    clips: Mapped[List['Clip']] = relationship(
        'Clip', back_populates='video', cascade='all, delete-orphan'
    )


class Clip(Base):
    """Represents an audio clip extracted from a video."""
    __tablename__ = 'clips'

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('videos.id'), index=True
    )
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    audio_path: Mapped[str] = mapped_column(String(1024))
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    video: Mapped['Video'] = relationship('Video', back_populates='clips')
    recordings: Mapped[List['Recording']] = relationship(
        'Recording', back_populates='clip', cascade='all, delete-orphan'
    )

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class Session(Base):
    """Represents a practice session."""
    __tablename__ = 'sessions'

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    recordings: Mapped[List['Recording']] = relationship(
        'Recording', back_populates='session', cascade='all, delete-orphan'
    )

    @property
    def duration_minutes(self) -> Optional[float]:
        if self.ended_at:
            delta = self.ended_at - self.started_at
            return delta.total_seconds() / 60
        return None


class Recording(Base):
    """Represents a user's audio recording attempt."""
    __tablename__ = 'recordings'

    id: Mapped[int] = mapped_column(primary_key=True)
    clip_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('clips.id'), nullable=True, index=True
    )
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('sessions.id'), nullable=True, index=True
    )
    audio_path: Mapped[str] = mapped_column(String(1024))
    filename: Mapped[str] = mapped_column(String(256))
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    clip: Mapped[Optional['Clip']] = relationship(
        'Clip', back_populates='recordings'
    )
    session: Mapped[Optional['Session']] = relationship(
        'Session', back_populates='recordings'
    )

