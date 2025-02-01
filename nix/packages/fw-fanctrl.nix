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
  pversion = "20-04-2024";
  description = "A simple systemd service to better control Framework Laptop's fan(s)";
  url = "https://github.com/TamtamHero/fw-fanctrl";
  setuptools_75_8_0 = python3Packages.setuptools.overrideAttrs (old: {
    version = "75.8.0";
    src = fetchFromGitHub {
      owner = "pypa";
      repo = "setuptools";
      rev = "v75.8.0";
      hash = "sha256-dSzsj0lnsc1Y+D/N0cnAPbS/ZYb+qC41b/KfPmL1zI4=";
    };
    patches = [];
  });
in
python3Packages.buildPythonPackage rec{
  pname = "fw-fanctrl";
  version = pversion;

  src = ../../.;

  outputs = [ "out" ];

  format = "pyproject";

  nativeBuildInputs = [
    python3
    getopt
    bash
  ];

  propagatedBuildInputs = [
    fw-ectool
    setuptools_75_8_0
  ];

  doCheck = false;

  meta = with lib; {
    mainProgram = "fw-fanctrl";
    homepage = url;
    description = description;
    platforms = with platforms; linux;
    license = licenses.bsd3;
    maintainers = with maintainers; [ "Svenum" ];
  };
}
