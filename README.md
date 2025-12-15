# Shadowing - Spanish Pronunciation Practice

A self-hosted web app for practicing Spanish pronunciation using the shadowing technique.

## Features

- **Audio Recording**: Record your pronunciation attempts directly in the browser
- **Clip Extraction**: Select clips from video files to practice
- **Spectrogram Visualization**: Compare your pronunciation with the original
- **Progress Tracking**: Keep track of all your recordings and practice sessions
- **Mobile-First Design**: Optimized for practicing on your phone
- **Self-Hosted**: Run on your homelab with access to your media library

## Quick Start

### Using devenv (Recommended for NixOS)

```bash
# Enter the development environment
devenv shell

# Start both backend and frontend
devenv up

# Or start them separately:
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm install && npm run dev -- --host 0.0.0.0
```

### Using Nix Flake

```bash
# Enter development shell
nix develop

# Run backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal
cd frontend && npm install && npm run dev -- --host 0.0.0.0
```

### Manual Setup

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

## Access

- **Frontend**: http://localhost:5173 (or your server IP)
- **API Docs**: http://localhost:8000/docs

Access from your phone by using your server's IP address instead of localhost.

## NixOS Deployment

Add to your NixOS configuration:

```nix
{
  imports = [ 
    inputs.shadowing.nixosModules.default 
  ];
  
  services.shadowing = {
    enable = true;
    port = 8000;
    dataDir = "/var/lib/shadowing";
    mediaDir = "/media";  # Where your videos are stored
  };
}
```

## Project Structure

```
shadowing/
├── backend/           # FastAPI Python backend
│   ├── app/
│   │   ├── api/       # API endpoints
│   │   ├── services/  # Business logic (FFmpeg, etc.)
│   │   ├── models.py  # Database models
│   │   └── main.py    # App entry point
│   └── requirements.txt
├── frontend/          # Vue 3 + Vite frontend
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   └── api/
│   └── package.json
├── data/              # Runtime data (created automatically)
│   ├── recordings/    # User recordings
│   ├── clips/         # Extracted audio clips
│   └── shadowing.db   # SQLite database
├── devenv.nix         # devenv configuration
├── flake.nix          # Nix flake for deployment
└── README.md
```

## How to Use

1. **Select a Video**: Enter the path to a video file on your server, or use the file browser
2. **Choose a Clip**: Set start and end times for the phrase you want to practice
3. **Listen**: Play the original audio to hear the pronunciation
4. **Record**: Record yourself saying the phrase
5. **Compare**: Listen to your recording and compare with the original
6. **Repeat**: Keep practicing until you're satisfied
7. **Move On**: Finish the clip and move to the next phrase

## Tips for Effective Shadowing

1. **Start Short**: Practice with clips of 5-15 seconds
2. **Focus on Rhythm**: Get the intonation and rhythm first, then work on individual sounds
3. **Multiple Attempts**: It's normal to record 10+ attempts per clip
4. **Use Spectrograms**: Visual comparison can help identify differences
5. **Practice Daily**: Consistency is more important than duration

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite, FFmpeg
- **Frontend**: Vue 3, Vite, Tailwind CSS, TypeScript
- **Audio**: Web Audio API, MediaRecorder API

## License

MIT

