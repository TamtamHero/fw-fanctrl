@setlocal

@cd /d "%~dp0"

fw-fanctrl run --config "####CONFIG_PATH####" --silent & ectool autofanctrl

@echo "waiting 5 seconds before retrying..."
@timeout 5 > NUL
