import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel


router = APIRouter()


# Allowed base paths for file browsing (can be configured)
ALLOWED_PATHS = [
    '/media',
    '/home',
    '/mnt',
]

# Video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.webm', '.mov', '.m4v', '.wmv', '.flv'}


class FileInfo(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    extension: Optional[str] = None


class DirectoryListing(BaseModel):
    path: str
    parent: Optional[str]
    files: List[FileInfo]


def is_path_allowed(path: str) -> bool:
    """Check if a path is within allowed directories."""
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(allowed) for allowed in ALLOWED_PATHS)


def is_video_file(path: Path) -> bool:
    """Check if a file is a video file."""
    return path.suffix.lower() in VIDEO_EXTENSIONS


@router.get('/files', response_model=DirectoryListing)
async def list_directory(
    path: str = Query('/', description='Directory path to list'),
    videos_only: bool = Query(False, description='Show only video files'),
):
    """
    List files and directories at the given path.
    """
    # Normalize and validate path
    target_path = Path(path).resolve()
    
    if not is_path_allowed(str(target_path)):
        raise HTTPException(
            status_code=403,
            detail=f'Access denied. Allowed paths: {ALLOWED_PATHS}'
        )
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail='Path not found')
    
    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail='Path is not a directory')
    
    files: List[FileInfo] = []
    
    try:
        for entry in sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip hidden files
            if entry.name.startswith('.'):
                continue
            
            is_dir = entry.is_dir()
            
            # Filter videos if requested
            if videos_only and not is_dir and not is_video_file(entry):
                continue
            
            file_info = FileInfo(
                name=entry.name,
                path=str(entry),
                is_dir=is_dir,
            )
            
            if not is_dir:
                try:
                    file_info.size = entry.stat().st_size
                    file_info.extension = entry.suffix.lower()
                except OSError:
                    pass
            
            files.append(file_info)
    
    except PermissionError:
        raise HTTPException(status_code=403, detail='Permission denied')
    
    # Get parent directory
    parent = str(target_path.parent) if target_path != target_path.parent else None
    if parent and not is_path_allowed(parent):
        parent = None
    
    return DirectoryListing(
        path=str(target_path),
        parent=parent,
        files=files,
    )


@router.get('/files/stream')
async def stream_file(
    path: str = Query(..., description='File path to stream'),
):
    """
    Stream a video file for playback.
    """
    file_path = Path(path).resolve()
    
    if not is_path_allowed(str(file_path)):
        raise HTTPException(status_code=403, detail='Access denied')
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='File not found')
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail='Path is not a file')
    
    # Determine media type
    ext_to_media = {
        '.mp4': 'video/mp4',
        '.mkv': 'video/x-matroska',
        '.avi': 'video/x-msvideo',
        '.webm': 'video/webm',
        '.mov': 'video/quicktime',
        '.m4v': 'video/mp4',
        '.wmv': 'video/x-ms-wmv',
        '.flv': 'video/x-flv',
    }
    media_type = ext_to_media.get(file_path.suffix.lower(), 'video/mp4')
    
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=file_path.name,
    )


@router.get('/files/info')
async def get_file_info(
    path: str = Query(..., description='File path to get info for'),
):
    """
    Get information about a file.
    """
    file_path = Path(path).resolve()
    
    if not is_path_allowed(str(file_path)):
        raise HTTPException(status_code=403, detail='Access denied')
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='File not found')
    
    stat = file_path.stat()
    
    return {
        'name': file_path.name,
        'path': str(file_path),
        'is_dir': file_path.is_dir(),
        'size': stat.st_size if file_path.is_file() else None,
        'extension': file_path.suffix.lower() if file_path.is_file() else None,
        'modified': stat.st_mtime,
    }

