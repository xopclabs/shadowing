{
  description = "Shadowing - Spanish pronunciation practice app";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        
        pythonPackages = pkgs.python311Packages;
        
        # Python backend package
        shadowingBackend = pythonPackages.buildPythonApplication {
          pname = "shadowing-backend";
          version = "0.1.0";
          
          src = ./backend;
          
          propagatedBuildInputs = with pythonPackages; [
            fastapi
            uvicorn
            sqlalchemy
            aiosqlite
            python-multipart
            pydantic
            pydantic-settings
          ];
          
          # Skip tests for now
          doCheck = false;
          
          meta = with pkgs.lib; {
            description = "Shadowing practice API backend";
            license = licenses.mit;
          };
        };
        
        # Frontend build
        shadowingFrontend = pkgs.buildNpmPackage {
          pname = "shadowing-frontend";
          version = "0.1.0";
          
          src = ./frontend;
          
          npmDepsHash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="; # Will need to be updated
          
          buildPhase = ''
            npm run build
          '';
          
          installPhase = ''
            mkdir -p $out
            cp -r dist/* $out/
          '';
          
          meta = with pkgs.lib; {
            description = "Shadowing practice frontend";
            license = licenses.mit;
          };
        };
        
      in {
        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Python
            python311
            pythonPackages.pip
            pythonPackages.virtualenv
            
            # Node.js
            nodejs_20
            
            # System tools
            ffmpeg
            git
            
            # For development
            pythonPackages.uvicorn
            pythonPackages.fastapi
            pythonPackages.sqlalchemy
            pythonPackages.aiosqlite
            pythonPackages.python-multipart
            pythonPackages.pydantic
            pythonPackages.pydantic-settings
          ];
          
          shellHook = ''
            export DATA_DIR="$PWD/data"
            export RECORDINGS_DIR="$PWD/data/recordings"
            export CLIPS_DIR="$PWD/data/clips"
            
            mkdir -p $DATA_DIR $RECORDINGS_DIR $CLIPS_DIR
            
            echo "Shadowing development environment"
            echo "  Python: $(python --version)"
            echo "  Node: $(node --version)"
            echo "  FFmpeg: $(ffmpeg -version 2>&1 | head -n1)"
            echo ""
            echo "To start development:"
            echo "  Backend:  cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
            echo "  Frontend: cd frontend && npm install && npm run dev -- --host 0.0.0.0"
          '';
        };
        
        # Packages
        packages = {
          backend = shadowingBackend;
          # frontend = shadowingFrontend;  # Uncomment after updating npmDepsHash
          default = shadowingBackend;
        };
      }
    ) // {
      # NixOS module for deployment
      nixosModules.default = { config, lib, pkgs, ... }:
        with lib;
        let
          cfg = config.services.shadowing;
        in {
          options.services.shadowing = {
            enable = mkEnableOption "Shadowing practice app";
            
            host = mkOption {
              type = types.str;
              default = "0.0.0.0";
              description = "Host to bind to";
            };
            
            port = mkOption {
              type = types.port;
              default = 8000;
              description = "Port to listen on";
            };
            
            dataDir = mkOption {
              type = types.path;
              default = "/var/lib/shadowing";
              description = "Directory for data storage";
            };
            
            mediaDir = mkOption {
              type = types.path;
              default = "/media";
              description = "Base directory for media files";
            };
            
            user = mkOption {
              type = types.str;
              default = "shadowing";
              description = "User to run the service as";
            };
            
            group = mkOption {
              type = types.str;
              default = "shadowing";
              description = "Group to run the service as";
            };
          };
          
          config = mkIf cfg.enable {
            users.users.${cfg.user} = {
              isSystemUser = true;
              group = cfg.group;
              home = cfg.dataDir;
              createHome = true;
            };
            
            users.groups.${cfg.group} = {};
            
            systemd.services.shadowing = {
              description = "Shadowing Practice App";
              wantedBy = [ "multi-user.target" ];
              after = [ "network.target" ];
              
              environment = {
                DATA_DIR = cfg.dataDir;
                RECORDINGS_DIR = "${cfg.dataDir}/recordings";
                CLIPS_DIR = "${cfg.dataDir}/clips";
              };
              
              serviceConfig = {
                Type = "simple";
                User = cfg.user;
                Group = cfg.group;
                WorkingDirectory = cfg.dataDir;
                ExecStart = "${pkgs.python311Packages.uvicorn}/bin/uvicorn app.main:app --host ${cfg.host} --port ${toString cfg.port}";
                Restart = "on-failure";
                RestartSec = 5;
                
                # Hardening
                NoNewPrivileges = true;
                ProtectSystem = "strict";
                ProtectHome = true;
                PrivateTmp = true;
                ReadWritePaths = [ cfg.dataDir cfg.mediaDir ];
              };
            };
            
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

