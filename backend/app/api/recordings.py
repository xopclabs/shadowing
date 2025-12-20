import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import Recording
from app.schemas import RecordingResponse, RecordingListResponse


router = APIRouter()


@router.post('/recordings/upload', response_model=RecordingResponse)
async def upload_recording(
    audio: UploadFile = File(...),
    clip_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_session),
):
    """
    Upload a new audio recording from the client.
    
    The audio file is saved to the recordings directory with a unique ID.
    """
    # Generate unique ID for this recording
    recording_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Determine file extension from content type
    content_type = audio.content_type or 'audio/webm'
    ext_map = {
        'audio/webm': '.webm',
        'audio/ogg': '.ogg',
        'audio/wav': '.wav',
        'audio/wave': '.wav',
        'audio/mp3': '.mp3',
        'audio/mpeg': '.mp3',
        'audio/mp4': '.m4a',
    }
    extension = ext_map.get(content_type, '.webm')
    
    # Create filename
    filename = f'{timestamp}_{recording_id}{extension}'
    filepath = settings.recordings_dir / filename
    
    # Save the file
    try:
        contents = await audio.read()
        with open(filepath, 'wb') as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to save recording: {str(e)}')
    
    # Calculate attempt number for this clip
    attempt_number = 1
    if clip_id:
        result = await db.execute(
            select(Recording).where(Recording.clip_id == clip_id)
        )
        existing = result.scalars().all()
        attempt_number = len(existing) + 1

    # Create database record
    recording = Recording(
        audio_path=str(filepath),
        filename=filename,
        clip_id=clip_id,
        attempt_number=attempt_number,
    )
    db.add(recording)
    await db.flush()
    await db.refresh(recording)
    
    return RecordingResponse(
        id=recording.id,
        filename=recording.filename,
        clip_id=recording.clip_id,
        attempt_number=recording.attempt_number,
        created_at=recording.created_at,
    )


@router.get('/recordings', response_model=RecordingListResponse)
async def list_recordings(
    clip_id: Optional[int] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    """List recordings, optionally filtered by clip."""
    query = select(Recording).order_by(Recording.created_at.desc()).limit(limit)
    
    if clip_id is not None:
        query = query.where(Recording.clip_id == clip_id)
    
    result = await db.execute(query)
    recordings = result.scalars().all()
    
    return RecordingListResponse(
        recordings=[
            RecordingResponse(
                id=r.id,
                filename=r.filename,
                clip_id=r.clip_id,
                attempt_number=r.attempt_number,
                created_at=r.created_at,
            )
            for r in recordings
        ]
    )


@router.get('/recordings/{filename}')
async def get_recording(filename: str):
    """Stream a recording file."""
    filepath = settings.recordings_dir / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail='Recording not found')
    
    # Determine media type
    ext_to_media = {
        '.webm': 'audio/webm',
        '.ogg': 'audio/ogg',
        '.wav': 'audio/wav',
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
    }
    media_type = ext_to_media.get(filepath.suffix, 'audio/webm')
    
    return FileResponse(filepath, media_type=media_type)


@router.delete('/recordings/{filename}')
async def delete_recording(
    filename: str,
    db: AsyncSession = Depends(get_session),
):
    """Delete a recording file and its database record."""
    filepath = settings.recordings_dir / filename
    
    # Delete from database
    result = await db.execute(
        select(Recording).where(Recording.filename == filename)
    )
    recording = result.scalar_one_or_none()
    
    if recording:
        await db.delete(recording)
    
    # Delete file
    if filepath.exists():
        try:
            filepath.unlink()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to delete file: {str(e)}')
    elif not recording:
        raise HTTPException(status_code=404, detail='Recording not found')
    
    return {'message': 'Recording deleted', 'filename': filename}
