@setlocal

@cd /d "%~dp0"

fw-fanctrl --run --config "####CONFIG_PATH####" --no-log --socket-controller win32 & ectool autofanctrl

@echo "waiting 5 seconds before retrying..."
@timeout 5 > NUL