{
  stdenv,
  lib
}:

stdenv.mkDerivation rec {
  version = "20-04-2024";
  name = "fw-ectool";
  src = ../../.;

  outputs = [ "out" ];

  installPhase = ''
    mkdir -p $out/bin/
    mv ./bin/ectool $out/bin/ectool
    ln -s $out/bin/ectool $out/bin/fw-ectool
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
