from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import Recording, Clip, Video, RecentFile
from app.schemas import (
    OverallStats,
    RecentFileResponse,
    RecentFileCreate,
    RecentFileListResponse,
    StorageInfo,
    DeleteFilesRequest,
)


router = APIRouter()


# ============ STATS ============

@router.get('/stats', response_model=OverallStats)
async def get_stats(
    db: AsyncSession = Depends(get_session),
):
    """Get overall practice statistics."""
    # Total recordings
    recordings_result = await db.execute(select(func.count(Recording.id)))
    total_recordings = recordings_result.scalar() or 0

    # Clips practiced (clips that have at least 1 recording)
    clips_practiced_result = await db.execute(
        select(func.count(func.distinct(Recording.clip_id)))
        .where(Recording.clip_id.isnot(None))
    )
    total_clips_practiced = clips_practiced_result.scalar() or 0

    # Calculate total practice time from clip durations * recordings
    # Get all clips that have recordings and sum their durations
    clips_with_recordings = await db.execute(
        select(Clip)
        .join(Recording, Recording.clip_id == Clip.id)
        .distinct()
    )
    clips = clips_with_recordings.scalars().all()
    
    # Get recording counts per clip
    recording_counts = {}
    for clip in clips:
        count_result = await db.execute(
            select(func.count(Recording.id)).where(Recording.clip_id == clip.id)
        )
        recording_counts[clip.id] = count_result.scalar() or 0
    
    # Total practice minutes = sum of (clip duration * number of recordings for that clip)
    total_practice_minutes = sum(
        clip.duration * recording_counts.get(clip.id, 0) / 60
        for clip in clips
    )

    # Recordings this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_result = await db.execute(
        select(func.count(Recording.id)).where(Recording.created_at >= week_ago)
    )
    recordings_this_week = week_result.scalar() or 0

    # First and last recording dates
    first_result = await db.execute(
        select(Recording.created_at).order_by(Recording.created_at.asc()).limit(1)
    )
    first_recording_date = first_result.scalar()

    last_result = await db.execute(
        select(Recording.created_at).order_by(Recording.created_at.desc()).limit(1)
    )
    last_recording_date = last_result.scalar()

    return OverallStats(
        total_recordings=total_recordings,
        total_clips_practiced=total_clips_practiced,
        total_practice_minutes=round(total_practice_minutes, 1),
        recordings_this_week=recordings_this_week,
        first_recording_date=first_recording_date,
        last_recording_date=last_recording_date,
    )


# ============ RECENT FILES ============

@router.get('/recent-files', response_model=RecentFileListResponse)
async def list_recent_files(
    limit: int = 10,
    db: AsyncSession = Depends(get_session),
):
    """List recently practiced video files."""
    result = await db.execute(
        select(RecentFile)
        .join(Video, Video.id == RecentFile.video_id)
        .order_by(RecentFile.last_used.desc())
        .limit(limit)
    )
    recent = result.scalars().all()

    files = []
    for rf in recent:
        # Get the video to extract path and filename
        video_result = await db.execute(
            select(Video).where(Video.id == rf.video_id)
        )
        video = video_result.scalar_one_or_none()
        if video:
            filename = Path(video.path).name
            files.append(RecentFileResponse(
                id=rf.id,
                video_path=video.path,
                filename=filename,
                last_timestamp=rf.last_timestamp,
                last_used=rf.last_used,
            ))

    return RecentFileListResponse(recent_files=files)


@router.post('/recent-files', response_model=RecentFileResponse)
async def add_recent_file(
    data: RecentFileCreate,
    db: AsyncSession = Depends(get_session),
):
    """Add or update a recent file entry."""
    # Get or create the video record
    video_result = await db.execute(
        select(Video).where(Video.path == data.video_path)
    )
    video = video_result.scalar_one_or_none()

    if not video:
        # Create video record
        video = Video(
            path=data.video_path,
            title=Path(data.video_path).stem,
        )
        db.add(video)
        await db.flush()
        await db.refresh(video)

    # Check if recent file entry exists
    recent_result = await db.execute(
        select(RecentFile).where(RecentFile.video_id == video.id)
    )
    recent = recent_result.scalar_one_or_none()

    if recent:
        # Update existing
        recent.last_timestamp = data.last_timestamp
        recent.last_used = datetime.utcnow()
    else:
        # Create new
        recent = RecentFile(
            video_id=video.id,
            last_timestamp=data.last_timestamp,
            last_used=datetime.utcnow(),
        )
        db.add(recent)

    await db.flush()
    await db.refresh(recent)

    return RecentFileResponse(
        id=recent.id,
        video_path=video.path,
        filename=Path(video.path).name,
        last_timestamp=recent.last_timestamp,
        last_used=recent.last_used,
    )


@router.delete('/recent-files/{file_id}')
async def delete_recent_file(
    file_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Delete a recent file entry."""
    result = await db.execute(
        select(RecentFile).where(RecentFile.id == file_id)
    )
    recent = result.scalar_one_or_none()

    if not recent:
        raise HTTPException(status_code=404, detail='Recent file not found')

    await db.delete(recent)

    return {'message': 'Recent file removed', 'id': file_id}


# ============ STORAGE MANAGEMENT ============

def get_directory_size(path: Path) -> tuple[int, int]:
    """Get total size and file count in a directory."""
    total_size = 0
    file_count = 0
    if path.exists():
        for f in path.iterdir():
            if f.is_file():
                total_size += f.stat().st_size
                file_count += 1
    return file_count, total_size


@router.get('/storage', response_model=StorageInfo)
async def get_storage_info():
    """Get storage usage information for clips and recordings."""
    clips_count, clips_size = get_directory_size(settings.clips_dir)
    recordings_count, recordings_size = get_directory_size(settings.recordings_dir)

    return StorageInfo(
        clips_count=clips_count,
        clips_size_bytes=clips_size,
        recordings_count=recordings_count,
        recordings_size_bytes=recordings_size,
        total_size_bytes=clips_size + recordings_size,
    )


@router.post('/storage/delete-files')
async def delete_local_files(
    request: DeleteFilesRequest,
    db: AsyncSession = Depends(get_session),
):
    """Delete local audio files (clips and/or recordings)."""
    deleted_clips = 0
    deleted_recordings = 0
    freed_bytes = 0

    if request.delete_clips:
        # Delete all clip audio files
        if settings.clips_dir.exists():
            for f in settings.clips_dir.iterdir():
                if f.is_file():
                    freed_bytes += f.stat().st_size
                    f.unlink()
                    deleted_clips += 1

        # Clear clips from database (this will cascade delete recordings)
        await db.execute(delete(Clip))

    if request.delete_recordings:
        # Delete all recording audio files
        if settings.recordings_dir.exists():
            for f in settings.recordings_dir.iterdir():
                if f.is_file():
                    freed_bytes += f.stat().st_size
                    f.unlink()
                    deleted_recordings += 1

        # Clear recordings from database
        await db.execute(delete(Recording))

    await db.commit()

    return {
        'deleted_clips': deleted_clips,
        'deleted_recordings': deleted_recordings,
        'freed_bytes': freed_bytes,
    }


@router.post('/database/clear')
async def clear_database(
    db: AsyncSession = Depends(get_session),
):
    """Clear all data from the database."""
    # Delete in order to respect foreign keys
    await db.execute(delete(Recording))
    await db.execute(delete(RecentFile))
    await db.execute(delete(Clip))
    await db.execute(delete(Video))

    await db.commit()

    return {'message': 'Database cleared successfully'}
