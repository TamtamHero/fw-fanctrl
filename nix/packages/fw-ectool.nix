{
  stdenv,
  lib,
  autoPatchelfHook,
  libusb1,
  libftdi1
}:

stdenv.mkDerivation {
  version = "20-04-2024";
  name = "fw-ectool";
  src = ../../.;

  outputs = [ "out" ];

  nativeBuildInputs = [
    autoPatchelfHook
  ];

  propagatedBuildInputs = [
    libusb1
    libftdi1
  ];

  installPhase = ''
    mkdir -p $out/bin
    runHook preInstall
    install -m755 ./bin/ectool $out/bin/ectool
    ln -s $out/bin/ectool $out/bin/fw-ectool
    chmod -R 755 $out/bin/*
  '';

  doCheck = false;

  meta = with lib; {
    mainProgram = "ectool";
    homepage = "https://github.com/TamtamHero/fw-fanctrl";
    description = "fw-ectool customized for fw-fanctrl";
    platforms = with platforms; linux;
    license = licenses.bsd3;
    maintainers = with maintainers; [ "Svenum" ];
  };
}
