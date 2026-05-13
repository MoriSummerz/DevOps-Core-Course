{ pkgs ? import <nixpkgs> { } }:

let
  python = pkgs.python3;

  # Exclude build outputs and editor/test caches so the source hash
  # stays stable across rebuilds. Without this, `result` (a symlink to
  # the previous build) would be hashed into `src` and every rebuild
  # would invalidate the cache.
  ignoredFiles = [
    "result" "result-bin" "result-dev"
    "__pycache__" ".pytest_cache" ".ruff_cache"
    ".venv" ".direnv" ".env" ".DS_Store"
    "default.nix" "docker.nix" "flake.nix" "flake.lock"
  ];

  filteredSrc = pkgs.lib.cleanSourceWith {
    src = ./.;
    filter = path: type:
      let baseName = baseNameOf path; in
      !(builtins.elem baseName ignoredFiles
        || pkgs.lib.hasSuffix ".pyc" baseName);
  };
in
python.pkgs.buildPythonApplication {
  pname = "devops-info-service";
  version = "1.0.0";
  src = filteredSrc;

  format = "other";

  propagatedBuildInputs = with python.pkgs; [
    fastapi
    uvicorn
    pydantic-settings
    prometheus-client
    python-json-logger
  ];

  nativeBuildInputs = [ pkgs.makeWrapper ];

  doCheck = false;

  installPhase = ''
    runHook preInstall

    mkdir -p $out/lib/devops-info-service $out/bin

    cp -r \
      app.py \
      config.py \
      lifespan.py \
      log_config.py \
      exception_handlers.py \
      metrics.py \
      middleware.py \
      dependencies \
      routes \
      $out/lib/devops-info-service/

    makeWrapper ${python.interpreter} $out/bin/devops-info-service \
      --add-flags "$out/lib/devops-info-service/app.py" \
      --prefix PYTHONPATH : "$out/lib/devops-info-service:$PYTHONPATH" \
      --set VISITS_FILE "/tmp/devops-info-visits"

    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "DevOps course info service - reproducibly built with Nix";
    homepage = "https://github.com/MoriSummerz/DevOps-Core-Course";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
