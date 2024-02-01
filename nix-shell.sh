#!/usr/bin/env bash

# selenium-driverless is unfree

d="$(dirname "$0")"

NIXPKGS_ALLOW_UNFREE=1 nix-shell $d/shell.nix
