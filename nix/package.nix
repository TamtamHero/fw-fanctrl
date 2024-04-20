{ 
lib,
lm_sensors,
python3Packages,
python3,
bash
}:

let
  pversion = "20-04-2024";
  description = "A simple systemd service to better control Framework Laptop's fan(s)";
  url = "https://github.com/TamtamHero/fw-fanctrl";
in
python3Packages.buildPythonPackage rec{
  pname = "fw-fanctrl";
  version = pversion;

  src = ../.;

  outputs = [ "out" ];

  preBuild = ''
    cat > setup.py << EOF
    from setuptools import setup

    with open("requirements.txt") as f:
        install_requires = f.read().splitlines()

    setup(
      name="fw-fanctrl",
      description="${description}",
      url="${url}",
      platforms=["linux"],

      install_requires=install_requires,
      scripts=[
        "fanctrl.py",
      ],
    )
    EOF
  '';

  nativeBuildInputs = [
    python3
  ];

  buildInputs = [
    lm_sensors
  ];

  propagatedBuildInputs = with python3Packages; [
    watchdog
  ];

  doCheck = false;

  postPatch = ''
    patchShebangs --build fanctrl.py
    substituteInPlace fanctrl.py --replace "/bin/bash" "${bash}/bin/bash"
    cat fanctrl.py
  '';

  installPhase = ''
    mkdir -p $out/bin 
    mv ./bin/ectool $out/bin/ectool
    mv ./fanctrl.py $out/bin/fw-fanctrl
    chmod 755 $out/bin/fw-fanctrl
  '';

  meta = with lib; {
    mainProgram = "fw-fanctrl";
    homepage = url;
    description = description;
    platforms = with platforms; linux;
    license = licenses.bsd3;
    maintainers = with maintainers; [ "TamtamHero" ];
  };
}
