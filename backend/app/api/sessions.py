from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Session, Recording
from app.schemas import SessionCreate, SessionResponse, SessionEnd


router = APIRouter()


@router.post('/sessions', response_model=SessionResponse)
async def create_session(
    session_data: Optional[SessionCreate] = None,
    db: AsyncSession = Depends(get_session),
):
    """Start a new practice session."""
    session = Session(
        notes=session_data.notes if session_data else None,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    
    return SessionResponse(
        id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        notes=session.notes,
        recording_count=0,
    )


@router.get('/sessions')
async def list_sessions(
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """List all practice sessions with recording counts."""
    # Query sessions with recording counts
    query = (
        select(Session, func.count(Recording.id).label('recording_count'))
        .outerjoin(Recording, Recording.session_id == Session.id)
        .group_by(Session.id)
        .order_by(Session.started_at.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    sessions = []
    for session, recording_count in rows:
        sessions.append(SessionResponse(
            id=session.id,
            started_at=session.started_at,
            ended_at=session.ended_at,
            notes=session.notes,
            duration_minutes=session.duration_minutes,
            recording_count=recording_count,
        ))
    
    return {'sessions': sessions}


@router.get('/sessions/{session_id}', response_model=SessionResponse)
async def get_session_detail(
    session_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Get session details by ID."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    
    # Get recording count
    count_result = await db.execute(
        select(func.count(Recording.id)).where(Recording.session_id == session_id)
    )
    recording_count = count_result.scalar() or 0
    
    return SessionResponse(
        id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        notes=session.notes,
        duration_minutes=session.duration_minutes,
        recording_count=recording_count,
    )


@router.patch('/sessions/{session_id}/end', response_model=SessionResponse)
async def end_session(
    session_id: int,
    end_data: Optional[SessionEnd] = None,
    db: AsyncSession = Depends(get_session),
):
    """End a practice session."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    
    if session.ended_at:
        raise HTTPException(status_code=400, detail='Session already ended')
    
    session.ended_at = datetime.utcnow()
    if end_data and end_data.notes:
        session.notes = end_data.notes
    
    await db.flush()
    
    # Get recording count
    count_result = await db.execute(
        select(func.count(Recording.id)).where(Recording.session_id == session_id)
    )
    recording_count = count_result.scalar() or 0
    
    return SessionResponse(
        id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        notes=session.notes,
        duration_minutes=session.duration_minutes,
        recording_count=recording_count,
    )


@router.delete('/sessions/{session_id}')
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Delete a session (recordings are cascade deleted)."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    
    await db.delete(session)
    
    return {'message': 'Session deleted', 'id': session_id}


@router.get('/stats')
async def get_stats(
    db: AsyncSession = Depends(get_session),
):
    """Get overall practice statistics."""
    from app.models import Clip
    
    # Total recordings
    recordings_result = await db.execute(select(func.count(Recording.id)))
    total_recordings = recordings_result.scalar() or 0
    
    # Total sessions
    sessions_result = await db.execute(select(func.count(Session.id)))
    total_sessions = sessions_result.scalar() or 0
    
    # Total clips
    clips_result = await db.execute(select(func.count(Clip.id)))
    total_clips = clips_result.scalar() or 0
    
    # Total practice time (from ended sessions)
    sessions_query = select(Session).where(Session.ended_at.isnot(None))
    sessions_result = await db.execute(sessions_query)
    sessions = sessions_result.scalars().all()
    
    total_minutes = sum(
        (s.duration_minutes or 0) for s in sessions
    )
    
    # Recordings this week
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_result = await db.execute(
        select(func.count(Recording.id)).where(Recording.created_at >= week_ago)
    )
    recordings_this_week = week_result.scalar() or 0
    
    # Average recordings per session
    avg_recordings = total_recordings / total_sessions if total_sessions > 0 else 0
    
    return {
        'total_recordings': total_recordings,
        'total_sessions': total_sessions,
        'total_clips': total_clips,
        'total_practice_minutes': round(total_minutes, 1),
        'recordings_this_week': recordings_this_week,
        'average_recordings_per_session': round(avg_recordings, 1),
    }
