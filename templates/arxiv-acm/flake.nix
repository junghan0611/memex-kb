{
  description = "ACM ArXiv Paper Environment";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }: {
    devShells.x86_64-linux.default = let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      tex = pkgs.texlive.combine {
        inherit (pkgs.texlive) scheme-full latexmk;
      };
    in pkgs.mkShell {
      buildInputs = [
        tex
        pkgs.emacs
      ];
    };
  };
}
