let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (python-pkgs: with python-pkgs; [
        pip
        python-dotenv
        pyyaml
        python-dateutil
        openai
    ]))
  ];
}
