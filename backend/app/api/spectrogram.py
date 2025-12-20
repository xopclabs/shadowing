from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import Clip
from app.services.spectrogram import spectrogram_service, SpectrogramError


router = APIRouter()


@router.get('/spectrogram/clip/id/{clip_id}')
async def get_clip_spectrogram_by_id(
    clip_id: int,
    max_duration: Optional[float] = Query(None, description='Max duration for scaling'),
    db: AsyncSession = Depends(get_session),
):
    """
    Generate spectrogram PNG for a clip by its database ID.
    
    Returns the spectrogram as a PNG image with the same visual style
    as the frontend JavaScript implementation.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f'Generating spectrogram for clip ID: {clip_id}')
    
    result = await db.execute(
        select(Clip).where(Clip.id == clip_id)
    )
    clip = result.scalar_one_or_none()
    
    if not clip:
        logger.warning(f'Clip not found: {clip_id}')
        raise HTTPException(status_code=404, detail='Clip not found')
    
    audio_path = Path(clip.audio_path)
    logger.info(f'Clip audio path: {audio_path}')
    
    if not audio_path.exists():
        logger.warning(f'Clip audio file not found: {audio_path}')
        raise HTTPException(status_code=404, detail=f'Clip audio file not found: {audio_path}')
    
    try:
        png_bytes, duration = await spectrogram_service.generate_spectrogram_png(
            str(audio_path),
            max_duration=max_duration,
        )
        
        return Response(
            content=png_bytes,
            media_type='image/png',
            headers={
                'X-Audio-Duration': str(duration),
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Expose-Headers': 'X-Audio-Duration',
            },
        )
        
    except SpectrogramError as e:
        logger.error(f'Spectrogram generation failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/spectrogram/clip/{filename}')
async def get_clip_spectrogram(
    filename: str,
    max_duration: Optional[float] = Query(None, description='Max duration for scaling'),
):
    """
    Generate spectrogram PNG for a clip audio file by filename.
    
    Returns the spectrogram as a PNG image with the same visual style
    as the frontend JavaScript implementation.
    """
    audio_path = settings.clips_dir / filename
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail='Clip audio not found')
    
    try:
        png_bytes, duration = await spectrogram_service.generate_spectrogram_png(
            str(audio_path),
            max_duration=max_duration,
        )
        
        return Response(
            content=png_bytes,
            media_type='image/png',
            headers={
                'X-Audio-Duration': str(duration),
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Expose-Headers': 'X-Audio-Duration',
            },
        )
        
    except SpectrogramError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/spectrogram/recording/{filename}')
async def get_recording_spectrogram(
    filename: str,
    max_duration: Optional[float] = Query(None, description='Max duration for scaling'),
):
    """
    Generate spectrogram PNG for a recording audio file.
    
    Returns the spectrogram as a PNG image with the same visual style
    as the frontend JavaScript implementation.
    """
    audio_path = settings.recordings_dir / filename
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail='Recording not found')
    
    try:
        png_bytes, duration = await spectrogram_service.generate_spectrogram_png(
            str(audio_path),
            max_duration=max_duration,
        )
        
        return Response(
            content=png_bytes,
            media_type='image/png',
            headers={
                'X-Audio-Duration': str(duration),
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Expose-Headers': 'X-Audio-Duration',
            },
        )
        
    except SpectrogramError as e:
        raise HTTPException(status_code=500, detail=str(e))

