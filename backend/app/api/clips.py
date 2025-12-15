from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import Video, Clip
from app.schemas import ClipExtractRequest, ClipResponse
from app.services.audio import audio_service, AudioExtractionError


router = APIRouter()


class ClipListResponse:
    def __init__(self, clips: list):
        self.clips = clips


@router.post('/clips/extract', response_model=ClipResponse)
async def extract_clip(
    request: ClipExtractRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Extract an audio clip from a video file.
    
    Takes a video path and time range, extracts the audio, and returns
    clip metadata including the audio file path.
    """
    # Validate time range
    if request.end_time <= request.start_time:
        raise HTTPException(
            status_code=400,
            detail='End time must be greater than start time'
        )

    # Validate video file exists
    video_path = Path(request.video_path)
    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f'Video file not found: {request.video_path}'
        )

    try:
        # Get or create video record
        result = await db.execute(
            select(Video).where(Video.path == request.video_path)
        )
        video = result.scalar_one_or_none()
        
        if not video:
            # Get video duration
            duration = await audio_service.get_video_duration(request.video_path)
            
            video = Video(
                path=request.video_path,
                title=video_path.stem,
                duration=duration,
            )
            db.add(video)
            await db.flush()
            await db.refresh(video)

        # Extract audio clip
        clip_uuid, audio_path = await audio_service.extract_audio_clip(
            video_path=request.video_path,
            start_time=request.start_time,
            end_time=request.end_time,
            output_format='mp3',
        )

        # Create clip record
        clip = Clip(
            video_id=video.id,
            start_time=request.start_time,
            end_time=request.end_time,
            audio_path=str(audio_path),
        )
        db.add(clip)
        await db.flush()
        await db.refresh(clip)

        return ClipResponse(
            id=clip.id,
            video_id=clip.video_id,
            start_time=clip.start_time,
            end_time=clip.end_time,
            audio_path=audio_path.name,
            duration=clip.duration,
            transcript=clip.transcript,
            created_at=clip.created_at,
        )

    except AudioExtractionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/clips')
async def list_clips(
    video_id: Optional[int] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    """List all extracted clips, optionally filtered by video."""
    query = select(Clip).order_by(Clip.created_at.desc()).limit(limit)
    
    if video_id is not None:
        query = query.where(Clip.video_id == video_id)
    
    result = await db.execute(query)
    clips = result.scalars().all()
    
    return {
        'clips': [
            ClipResponse(
                id=clip.id,
                video_id=clip.video_id,
                start_time=clip.start_time,
                end_time=clip.end_time,
                audio_path=Path(clip.audio_path).name,
                duration=clip.duration,
                transcript=clip.transcript,
                created_at=clip.created_at,
            )
            for clip in clips
        ]
    }


@router.get('/clips/{clip_id}', response_model=ClipResponse)
async def get_clip(
    clip_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Get clip metadata by ID."""
    result = await db.execute(
        select(Clip).where(Clip.id == clip_id)
    )
    clip = result.scalar_one_or_none()
    
    if not clip:
        raise HTTPException(status_code=404, detail='Clip not found')
    
    return ClipResponse(
        id=clip.id,
        video_id=clip.video_id,
        start_time=clip.start_time,
        end_time=clip.end_time,
        audio_path=Path(clip.audio_path).name,
        duration=clip.duration,
        transcript=clip.transcript,
        created_at=clip.created_at,
    )


@router.get('/clips/{clip_id}/audio')
async def get_clip_audio(
    clip_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Stream the audio file for a clip."""
    result = await db.execute(
        select(Clip).where(Clip.id == clip_id)
    )
    clip = result.scalar_one_or_none()
    
    if not clip:
        raise HTTPException(status_code=404, detail='Clip not found')
    
    audio_path = Path(clip.audio_path)
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail='Audio file not found')
    
    # Determine media type
    ext_to_media = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
    }
    media_type = ext_to_media.get(audio_path.suffix, 'audio/mpeg')
    
    return FileResponse(
        audio_path,
        media_type=media_type,
        filename=audio_path.name,
    )


@router.delete('/clips/{clip_id}')
async def delete_clip(
    clip_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Delete a clip and its audio file."""
    result = await db.execute(
        select(Clip).where(Clip.id == clip_id)
    )
    clip = result.scalar_one_or_none()
    
    if not clip:
        raise HTTPException(status_code=404, detail='Clip not found')
    
    audio_path = Path(clip.audio_path)
    
    # Delete audio file if it exists
    if audio_path.exists():
        audio_path.unlink()
    
    # Delete from database
    await db.delete(clip)
    
    return {'message': 'Clip deleted', 'id': clip_id}
