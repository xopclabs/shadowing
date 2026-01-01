import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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


# Health check endpoint (before static files catch-all)
@app.get('/health')
async def health_check():
    return {'status': 'healthy'}


# Static file serving for production (when STATIC_DIR is set)
STATIC_DIR = os.environ.get('STATIC_DIR')
if STATIC_DIR and Path(STATIC_DIR).exists():
    # Mount static assets (js, css, images, etc.)
    app.mount('/assets', StaticFiles(directory=Path(STATIC_DIR) / 'assets'), name='assets')

    # SPA catch-all: serve index.html for any non-API, non-asset route
    @app.get('/{full_path:path}')
    async def serve_spa(request: Request, full_path: str):
        """Serve the SPA index.html for client-side routing."""
        # Don't interfere with API routes
        if full_path.startswith('api/') or full_path == 'health':
            return {'error': 'not found'}

        # Try to serve the exact file if it exists
        file_path = Path(STATIC_DIR) / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # Otherwise serve index.html for SPA routing
        return FileResponse(Path(STATIC_DIR) / 'index.html')
else:
    # Development mode: just serve API info at root
    @app.get('/')
    async def root():
        return {
            'message': 'Shadowing Practice API',
            'version': '0.1.0',
            'docs_url': '/docs',
        }
