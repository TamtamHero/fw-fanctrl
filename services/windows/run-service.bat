@setlocal

@cd /d "%~dp0"

fw-fanctrl run --config "####CONFIG_PATH####" --silent ####NO_BATTERY_SENSOR_OPTION#### & ectool autofanctrl

@echo "waiting 5 seconds before retrying..."
@timeout 5 > NUL
