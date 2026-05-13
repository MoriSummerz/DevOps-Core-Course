{
  description = "DevOps Info Service - Reproducible Build with Nix Flakes (Lab 18)";

  inputs = {
    # nixos-25.11 is the first stable channel that ships fakeroot 1.37.2,
    # which is needed for dockerTools to work on macOS 26 (older fakeroot
    # 1.36 references the removed `_fstat$INODE64` dyld symbol).
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = import ./default.nix { inherit pkgs; };
          dockerImage = import ./docker.nix { inherit pkgs; };
        }
      );

      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python3
              python3Packages.fastapi
              python3Packages.uvicorn
              python3Packages.pydantic-settings
              python3Packages.prometheus-client
              python3Packages.python-json-logger
              python3Packages.pytest
              ruff
            ];
            shellHook = ''
              echo "==> Nix dev shell: DevOps Info Service"
              echo "    Python: $(python --version)"
              echo "    Flake : $(${pkgs.coreutils}/bin/basename $PWD)"
              export VISITS_FILE=/tmp/devops-info-visits
            '';
          };
        }
      );
    };
}
