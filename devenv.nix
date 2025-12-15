{ pkgs, lib, config, inputs, ... }:

{
  # Environment variables
  env = {
    DATA_DIR = "${config.env.DEVENV_ROOT}/data";
    RECORDINGS_DIR = "${config.env.DEVENV_ROOT}/data/recordings";
    CLIPS_DIR = "${config.env.DEVENV_ROOT}/data/clips";
  };

  # System packages
  packages = with pkgs; [
    ffmpeg
    git
  ];

  # Python environment
  languages.python = {
    enable = true;
    version = "3.11";
    venv = {
      enable = true;
      requirements = ./backend/requirements.txt;
    };
  };

  # Node.js environment
  languages.javascript = {
    enable = true;
    package = pkgs.nodejs_20;
    npm.enable = true;
  };

  # Create data directories on shell enter
  enterShell = ''
    mkdir -p $DATA_DIR $RECORDINGS_DIR $CLIPS_DIR
    echo "Shadowing app development environment ready!"
    echo "  - Python: $(python --version)"
    echo "  - Node: $(node --version)"
    echo "  - FFmpeg: $(ffmpeg -version | head -n1)"
  '';

  # Process management for development
  processes = {
    backend.exec = "cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000";
    frontend.exec = "cd frontend && npm install && npm run dev -- --host 0.0.0.0";
  };

  # Pre-commit hooks (optional but nice)
  pre-commit.hooks = {
    ruff.enable = true;
    prettier.enable = true;
  };
}

