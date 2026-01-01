# Shadowing

> ⚠️ **THIS THING IS ENTIRELY VIBECODED** ⚠️
>
> This entire project was vibecoded Claude Opus 4.5 for my personal use. 
> It works on my machine and has (or will have) feature I want and need and that's about all I can guarantee.
>
> **Not intended for public use. No support provided. Use at your own risk.**
>
> If you're reading this and you're not me: you probably want to build your own 
> thing instead of trying to make sense of this chaos.
> I basically only made it public so I can pull it in my flake easily...

---

A self-hosted app for practicing Spanish pronunciation using the shadowing technique. 
Extracts clips from video files, lets you record yourself, and compares the audio.

## What it does

- Browse video files on my server
- Extract audio clips at specific timestamps
- Record my pronunciation attempts in the browser
- View spectrograms to compare original vs my attempt
- Track practice sessions

## Running it

### Development (with devenv)

```bash
devenv shell
devenv up
```

### Development (with nix)

```bash
nix develop
cd backend && uvicorn app.main:app --reload --port 8847 &
cd frontend && npm install && npm run dev
```

### NixOS Deployment

The flake provides a NixOS module:

```nix
{
  services.shadowing = {
    enable = true;
    port = 8847;
    dataDir = "/var/lib/shadowing";
    mediaDir = "/path/to/videos";
  };
}
```

## Stack

- **Backend**: FastAPI, SQLite, FFmpeg
- **Frontend**: Vue 3, Vite, Tailwind
- **Deployment**: NixOS module via flake
