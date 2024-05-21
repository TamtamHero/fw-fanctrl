{ 
lib,
lm_sensors,
python3Packages,
python3,
bash,
callPackage
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
  ];

  propagatedBuildInputs = with python3Packages; [
    watchdog
    (callPackage ./fw-ectool.nix {})
    lm_sensors
  ];

  doCheck = false;

  postPatch = ''
    patchShebangs --build fanctrl.py
    substituteInPlace fanctrl.py --replace "/bin/bash" "${bash}/bin/bash"
    cat fanctrl.py
  '';

  installPhase = ''
    mkdir -p $out/bin 
    mv ./fanctrl.py $out/bin/fw-fanctrl
    chmod 755 $out/bin/fw-fanctrl
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
