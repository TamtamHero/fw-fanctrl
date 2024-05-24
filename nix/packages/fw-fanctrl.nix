{ 
lib,
python3Packages,
python3,
bash,
callPackage,
getopt
}:

let
  pversion = "20-04-2024";
  description = "A simple systemd service to better control Framework Laptop's fan(s)";
  url = "https://github.com/TamtamHero/fw-fanctrl";
in
python3Packages.buildPythonPackage rec{
  pname = "fw-fanctrl";
  version = pversion;

  src = ../../.;

  outputs = [ "out" ];

  preBuild = ''
    cat > setup.py << EOF
    from setuptools import setup

    setup(
      name="fw-fanctrl",
      description="${description}",
      url="${url}",
      platforms=["linux"],
      py_modules=[],

      scripts=[
        "fanctrl.py",
      ],
    )
    EOF
  '';

  nativeBuildInputs = [
    python3
    getopt
  ];

  propagatedBuildInputs = [
    (callPackage ./fw-ectool.nix {})
  ];

  doCheck = false;

  postPatch = ''
    patchShebangs --build fanctrl.py
    patchShebangs --build install.sh
    substituteInPlace fanctrl.py --replace "/bin/bash" "${bash}/bin/bash"
    cat fanctrl.py
  '';

  installPhase = ''
    ./install.sh --dest-dir $out --prefix-dir "" --no-ectool --no-post-install 
  '';

  meta = with lib; {
    mainProgram = "fw-fanctrl";
    homepage = url;
    description = description;
    platforms = with platforms; linux;
    license = licenses.bsd3;
    maintainers = with maintainers; [ "Svenum" ];
  };
}
