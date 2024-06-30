{
  description = "A simple systemd service to better control Framework Laptop's fan(s)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";

    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, flake-compat }: {
    packages.x86_64-linux.default = self.packages.x86_64-linux.fw-fanctrl;
    packages.x86_64-linux.fw-fanctrl = (
      import nixpkgs {
        currentSystem = "x86_64-linux";
        localSystem = "x86_64-linux";
      }).pkgs.callPackage ./nix/packages/fw-fanctrl.nix {};

    nixosModules.default = import ./nix/module.nix;
  };
}
