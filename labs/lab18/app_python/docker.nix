{ pkgs ? import <nixpkgs> { } }:

let
  app = import ./default.nix { inherit pkgs; };
in
pkgs.dockerTools.buildLayeredImage {
  name = "devops-info-service-nix";
  tag = "1.0.0";

  # Minimal closure: only what the FastAPI service actually needs.
  # No base image (no `python:3.12-slim`), no shell, no extra utilities.
  contents = [ app ];

  config = {
    Cmd = [ "${app}/bin/devops-info-service" ];
    ExposedPorts = {
      "5000/tcp" = { };
    };
    Env = [
      "VISITS_FILE=/tmp/devops-info-visits"
      "PORT=5000"
      "HOST=0.0.0.0"
    ];
    WorkingDir = "/";
  };

  # Reproducible timestamp - DO NOT use "now"
  created = "1970-01-01T00:00:01Z";
}
