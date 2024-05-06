{
  description = "A software to controll the Framework fan speed";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";

    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, flake-compat }: {

    packages.x86_64-linux.fw-fanctrl = (
      import nixpkgs {
        currentSystem = "x86_64-linux";
        localSystem = "x86_64-linux";
      }).pkgs.callPackage ./nix/packages/fw-fanctrl.nix { inherit self; };

    packages.x86_64-linux.fw-ectool = (
      import nixpkgs {
        currentSystem = "x86_64-linux";
        localSystem = "x86_64-linux";
      }).pkgs.callPackage ./nix/packages/fw-ectool.nix {};

    nixosModules.default = import ./nix/module.nix;
  };
}
