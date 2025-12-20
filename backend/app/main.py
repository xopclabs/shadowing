from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api import clips, files, recordings, sessions, spectrogram


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown events."""
    # Startup
    settings.ensure_directories()
    await init_db()
    yield
    # Shutdown (nothing to do for now)


app = FastAPI(
    title='Shadowing Practice API',
    description='API for Spanish pronunciation shadowing practice',
    version='0.1.0',
    lifespan=lifespan,
)

# Configure CORS for development (access from mobile devices on LAN)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['X-Audio-Duration'],
)

# Include routers
app.include_router(recordings.router, prefix=settings.api_prefix, tags=['recordings'])
app.include_router(clips.router, prefix=settings.api_prefix, tags=['clips'])
app.include_router(sessions.router, prefix=settings.api_prefix, tags=['sessions'])
app.include_router(files.router, prefix=settings.api_prefix, tags=['files'])
app.include_router(spectrogram.router, prefix=settings.api_prefix, tags=['spectrogram'])


@app.get('/')
async def root():
    return {
        'message': 'Shadowing Practice API',
        'version': '0.1.0',
        'docs_url': '/docs',
    }


@app.get('/health')
async def health_check():
    return {'status': 'healthy'}
