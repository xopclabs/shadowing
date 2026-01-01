{
  description = "Shadowing - Spanish pronunciation practice app";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
      # Helper to create packages for a given pkgs instance
      mkPackages = pkgs: rec {
        # Backend source as a derivation
        backendSrc = pkgs.stdenv.mkDerivation {
          pname = "shadowing-backend-src";
          version = "0.1.0";
          src = ./backend;
          phases = [ "installPhase" ];
          installPhase = ''
            mkdir -p $out
            cp -r $src/* $out/
          '';
        };
        
        # Python environment with all dependencies
        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          fastapi
          uvicorn
          sqlalchemy
          aiosqlite
          python-multipart
          pydantic
          pydantic-settings
          numpy
        ]);
        
        # Wrapper script to run the backend
        backend = pkgs.writeShellApplication {
          name = "shadowing-backend";
          runtimeInputs = [ pythonEnv pkgs.ffmpeg ];
          text = ''
            cd ${backendSrc}
            exec ${pythonEnv}/bin/uvicorn app.main:app "$@"
          '';
        };
        
        # Frontend build
        frontend = pkgs.buildNpmPackage {
          pname = "shadowing-frontend";
          version = "0.1.0";
          src = ./frontend;
          npmDepsHash = "sha256-IAFZziEjoAouciIpMhOIKGtWEatZuk4gafeahNS4mLs=";
          buildPhase = ''
            runHook preBuild
            npm run build -- --mode production || npm exec vite build
            runHook postBuild
          '';
          installPhase = ''
            runHook preInstall
            mkdir -p $out
            cp -r dist/* $out/
            runHook postInstall
          '';
        };
      };
    in
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        packages = mkPackages pkgs;
      in {
        packages = {
          inherit (packages) backend frontend;
          default = packages.backend;
        };
        
        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Python
            python311
            python311Packages.pip
            python311Packages.virtualenv
            
            # Node.js
            nodejs_20
            
            # System tools
            ffmpeg
            git
            
            # Python dependencies for development
            python311Packages.uvicorn
            python311Packages.fastapi
            python311Packages.sqlalchemy
            python311Packages.aiosqlite
            python311Packages.python-multipart
            python311Packages.pydantic
            python311Packages.pydantic-settings
            python311Packages.numpy
          ];
          
          shellHook = ''
            export DATA_DIR="$PWD/data"
            export RECORDINGS_DIR="$PWD/data/recordings"
            export CLIPS_DIR="$PWD/data/clips"
            export BACKEND_PORT="''${BACKEND_PORT:-8847}"
            export FRONTEND_PORT="''${FRONTEND_PORT:-8848}"
            
            mkdir -p $DATA_DIR $RECORDINGS_DIR $CLIPS_DIR
            
            echo "Shadowing development environment"
            echo "  Python: $(python --version)"
            echo "  Node: $(node --version)"
            echo "  FFmpeg: $(ffmpeg -version 2>&1 | head -n1)"
            echo ""
            echo "Ports: Backend=$BACKEND_PORT, Frontend=$FRONTEND_PORT"
            echo ""
            echo "To start development:"
            echo "  Backend:  cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT"
            echo "  Frontend: cd frontend && npm install && npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT"
          '';
        };
      }
    ) // {
      # NixOS module for deployment
      nixosModules.default = { config, lib, pkgs, ... }:
        let
          cfg = config.services.shadowing;
          packages = mkPackages pkgs;
        in {
          options.services.shadowing = {
            enable = lib.mkEnableOption "Shadowing practice app";
            
            host = lib.mkOption {
              type = lib.types.str;
              default = "0.0.0.0";
              description = "Host to bind to";
            };
            
            port = lib.mkOption {
              type = lib.types.port;
              default = 8847;
              description = "Port for the service (serves both API and frontend)";
            };
            
            dataDir = lib.mkOption {
              type = lib.types.path;
              default = "/var/lib/shadowing";
              description = "Directory for data storage";
            };
            
            mediaDir = lib.mkOption {
              type = lib.types.nullOr lib.types.path;
              default = null;
              description = "Base directory for media files (optional, for browsing external media)";
            };
            
            user = lib.mkOption {
              type = lib.types.str;
              default = "shadowing";
              description = "User to run the service as";
            };
            
            group = lib.mkOption {
              type = lib.types.str;
              default = "shadowing";
              description = "Group to run the service as";
            };
            
            openFirewall = lib.mkOption {
              type = lib.types.bool;
              default = false;
              description = "Open firewall for the service port";
            };
          };
          
          config = lib.mkIf cfg.enable {
            # User and group
            users.users.${cfg.user} = {
              isSystemUser = true;
              group = cfg.group;
              home = cfg.dataDir;
              createHome = true;
            };
            
            users.groups.${cfg.group} = {};
            
            # Shadowing service (FastAPI serves both API and static frontend)
            systemd.services.shadowing = {
              description = "Shadowing Practice App";
              wantedBy = [ "multi-user.target" ];
              after = [ "network.target" ];
              
              environment = {
                DATA_DIR = cfg.dataDir;
                RECORDINGS_DIR = "${cfg.dataDir}/recordings";
                CLIPS_DIR = "${cfg.dataDir}/clips";
                STATIC_DIR = "${packages.frontend}";
              } // lib.optionalAttrs (cfg.mediaDir != null) {
                MEDIA_DIR = cfg.mediaDir;
              };
              
              serviceConfig = {
                Type = "simple";
                User = cfg.user;
                Group = cfg.group;
                ExecStart = "${packages.backend}/bin/shadowing-backend --host ${cfg.host} --port ${toString cfg.port}";
                Restart = "on-failure";
                RestartSec = 5;
                
                # Hardening
                NoNewPrivileges = true;
                ProtectSystem = "strict";
                ProtectHome = true;
                PrivateTmp = true;
                ReadWritePaths = [ cfg.dataDir ] ++ lib.optional (cfg.mediaDir != null) cfg.mediaDir;
              };
            };
            
            # Open firewall if requested
            networking.firewall.allowedTCPPorts = lib.mkIf cfg.openFirewall [ cfg.port ];
            
            # Create data directories
            systemd.tmpfiles.rules = [
              "d ${cfg.dataDir} 0750 ${cfg.user} ${cfg.group} -"
              "d ${cfg.dataDir}/recordings 0750 ${cfg.user} ${cfg.group} -"
              "d ${cfg.dataDir}/clips 0750 ${cfg.user} ${cfg.group} -"
            ];
          };
        };
    };
}
