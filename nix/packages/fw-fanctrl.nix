{
lib,
python3Packages,
python3,
bash,
callPackage,
getopt,
fw-ectool,
fetchFromGitHub
}:

let
  setuptools_custom = python3Packages.setuptools.overrideAttrs (old: rec {
    version = "75.8.2";
    src = fetchFromGitHub {
      owner = "pypa";
      repo = "setuptools";
      rev = "v${version}";
      hash = "sha256-nD6c2JOjBL/SfgNchBlNasuwnrRl6XIuppjOt6Hr7CE=";
    };
    patches = [];
  });
in
python3Packages.buildPythonPackage rec{
  pname = "fw-fanctrl";
  version = "09-03-2025";

  src = ../../.;

  outputs = [ "out" ];

  format = "pyproject";

  nativeBuildInputs = [
    python3
  ];

  propagatedBuildInputs = with python3Packages; [
    fw-ectool
    setuptools_custom
    jsonschema
  ];

  doCheck = false;

  meta = with lib; {
    mainProgram = "fw-fanctrl";
    homepage = "https://github.com/TamtamHero/fw-fanctrl";
    description = "A simple systemd service to better control Framework Laptop's fan(s)";
    platforms = with platforms; linux;
    license = licenses.bsd3;
    maintainers = with maintainers; [ "Svenum" ];
  };
}
