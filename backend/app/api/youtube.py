from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import YouTubeDownload
from app.schemas import YouTubeDownloadResponse, YouTubeDownloadListResponse
from app.services.youtube import youtube_service, VideoInfo, DownloadResult, YouTubeDownloadError


router = APIRouter()


class YouTubeDownloadRequest(BaseModel):
    """Request to download a YouTube video."""
    url: str
    audio_only: bool = False


class YouTubeInfoRequest(BaseModel):
    """Request to get YouTube video info."""
    url: str


@router.post('/youtube/info', response_model=VideoInfo)
async def get_video_info(request: YouTubeInfoRequest):
    """
    Get information about a YouTube video without downloading.

    Returns video title, duration, thumbnail, and other metadata.
    """
    try:
        return await youtube_service.get_video_info(request.url)
    except YouTubeDownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/youtube/download', response_model=DownloadResult)
async def download_video(
    request: YouTubeDownloadRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Download a YouTube video.

    If audio_only is True, downloads only the audio as MP3.
    Otherwise, downloads the video as MP4.

    Uses the configured SOCKS5 proxy if set in server settings.
    """
    try:
        # Get video info first
        info = await youtube_service.get_video_info(request.url)

        # Download the video
        result = await youtube_service.download_video(
            url=request.url,
            audio_only=request.audio_only,
        )

        # If successful, save to database
        if result.success and result.file_path:
            # Check if already exists
            existing = await db.execute(
                select(YouTubeDownload).where(YouTubeDownload.video_id == result.video_id)
            )
            download_record = existing.scalar_one_or_none()

            if download_record:
                # Update existing record
                download_record.file_path = result.file_path
                download_record.is_audio_only = request.audio_only
            else:
                # Create new record
                download_record = YouTubeDownload(
                    video_id=result.video_id,
                    title=result.title,
                    file_path=result.file_path,
                    thumbnail_url=info.thumbnail,
                    duration=info.duration,
                    uploader=info.uploader,
                    is_audio_only=request.audio_only,
                )
                db.add(download_record)

            await db.commit()

        return result
    except YouTubeDownloadError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/youtube/downloads', response_model=YouTubeDownloadListResponse)
async def list_downloads(
    db: AsyncSession = Depends(get_session),
):
    """List all downloaded YouTube videos."""
    result = await db.execute(
        select(YouTubeDownload).order_by(YouTubeDownload.created_at.desc())
    )
    downloads = result.scalars().all()

    # Filter out downloads where file no longer exists
    valid_downloads = []
    for download in downloads:
        if Path(download.file_path).exists():
            valid_downloads.append(download)

    return YouTubeDownloadListResponse(downloads=valid_downloads)


@router.delete('/youtube/downloads/{download_id}')
async def delete_download(
    download_id: int,
    delete_file: bool = False,
    db: AsyncSession = Depends(get_session),
):
    """Delete a YouTube download record, optionally deleting the file too."""
    result = await db.execute(
        select(YouTubeDownload).where(YouTubeDownload.id == download_id)
    )
    download = result.scalar_one_or_none()

    if not download:
        raise HTTPException(status_code=404, detail='Download not found')

    if delete_file:
        file_path = Path(download.file_path)
        if file_path.exists():
            file_path.unlink()

    await db.delete(download)
    await db.commit()

    return {'message': 'Download deleted', 'id': download_id}
