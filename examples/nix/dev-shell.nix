{ pkgs ? import <nixpkgs> {} }:
let
  baseShell = pkgs.callPackage ../shell.nix { pkgs = pkgs ; };
in
  baseShell.overrideAttrs (finalAttrs: previousAttrs: {
    nativeBuildInputs = previousAttrs.nativeBuildInputs ++ [ pkgs.helix pkgs.claude-code ];
  })
