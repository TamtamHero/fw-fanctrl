@echo off

setlocal

for /F "delims=#" %%E in ('"prompt #$E# & for %%E in (1) do rem"') do set "ESC=%%E"

:: Check if the script is running with administrative privileges
net session > nul 2>&1
:: If not, relaunch the script with elevated privileges
if %errorLevel% neq 0 (
    echo requesting administrative privileges...
    :: Check if there are arguments
    if "%~1"=="" (
        PowerShell -Command "Start-Process '%~f0' -Verb runAs"
    ) else (
        PowerShell -Command "Start-Process '%~f0' -ArgumentList '%*' -Verb runAs"
    )
    exit /b
)

echo running with administrative privileges...

set "ARG_remove="
set "ARG_r="

CALL :ARG-PARSER %*

if defined ARG_r (
    if not defined ARG_remove set "ARG_remove=%ARG_r%"
)

cd /d "%~dp0"

if not defined ARG_remove (
    GOTO :ACKNOWLEDGEMENT-CHECK
)

if defined ARG_remove (
    echo:
    echo ----------
    CALL :UNINSTALL
)

GOTO :EOF

:ACKNOWLEDGEMENT-CHECK
    set "acknowledgementPhrase=this is dangerous and I know what I am doing"
    echo %ESC%[91m
    echo ====================================== WARNING ======================================
    echo 1. THIS WINDOWS VERSION REQUIRES THE USE OF AN UNSIGNED 'crosec' DRIVER TO WORK.
    echo 2. SECURE BOOT MUST BE DISABLED IN ORDER TO USE THE PROGRAM
    echo 3. IF YOU HAVE BITLOCKER ENABLED, YOU WILL NEED YOUR RECOVERY CODE ON BOOT !!!!
    echo ====================================== WARNING ======================================
    echo PLEASE MAKE A BACKUP OF YOUR BITLOCKER RECOVERY KEY BEFORE YOU DO ANYTHING !
    echo YOU GET LOCKED OUT OF YOUR COMPUTER IF YOU ARE NOT CAREFUL ENOUGH !
    echo PROCEED WITH THE INSTALLATION IF YOU ARE ABSOLUTELY SURE OF WHAT YOU ARE DOING !
    echo -------------------------------------------------------------------------------------
    echo %ESC%[0m
    echo to continue the installation, type '%acknowledgementPhrase%'.
    echo to stop here, simply press enter.
    set "acknowledgement="
    set /p "acknowledgement=> "
    if not defined acknowledgement (
        echo goodbye.
        exit /b 2
    )
    if not "%acknowledgement%" equ "%acknowledgementPhrase%" (
        echo wrong acknowledgement phrase [%acknowledgement%] not equal to [%acknowledgementPhrase%], stopping here!
        exit /b 2
    )
    echo:
    echo ----------
    CALL :INSTALL
    GOTO :EOF

:INSTALL
    CALL :UNINSTALL

    "%localAppData%\Programs\Python\Python312\python" --version
    if %errorLevel% neq 0 (
       echo python 3.12.x is required to use 'fw-fanctrl'
       echo please install it from the official website https://www.python.org/ before running this script
       GOTO :EOF
    )

    echo installing

    set "addedEnvironmentPaths="

    echo:
    echo ----------
    CALL :install-crosec
    if %errorLevel% neq 0 (
       echo failed to install 'crosec'
       GOTO UNINSTALL
    )

    echo:
    echo ----------
    CALL :install-ectool
    if %errorLevel% neq 0 (
       echo failed to install 'ectool'
       GOTO UNINSTALL
    )

    echo:
    echo ----------
    CALL :install-nssm
    if %errorLevel% neq 0 (
       echo failed to install 'nssm'
       GOTO UNINSTALL
    )

    echo:
    echo ----------
    CALL :install-fw-fanctrl
    if %errorLevel% neq 0 (
       echo failed to install 'fw-fanctrl'
       GOTO UNINSTALL
    )

    if defined addedEnvironmentPaths (
        echo adding '%addedEnvironmentPaths%' to path
        @echo on
        powershell -Command "[System.Environment]::SetEnvironmentVariable('Path', $env:Path+'%addedEnvironmentPaths%', [System.EnvironmentVariableTarget]::Machine)"
        powershell -Command "[System.Environment]::SetEnvironmentVariable('Path', [System.Environment]::GetEnvironmentVariable('Path', [System.EnvironmentVariableTarget]::Machine) + ';' + [System.Environment]::GetEnvironmentVariable('Path', [System.EnvironmentVariableTarget]::User), [System.EnvironmentVariableTarget]::Process)"
        @echo off
    )

    echo starting 'fw-fanctrl' service
    @echo on
    "%ProgramFiles%\nssm\nssm" start "fw-fanctrl"
    "%ProgramFiles%\nssm\nssm" continue "fw-fanctrl"
    @echo off
    if %errorLevel% neq 0 (
       echo failed to start 'fw-fanctrl' service
    )

    rmdir /s /q ".temp" 2> nul

    pause
    GOTO :EOF

    :install-crosec
        echo setting up 'crosec'
        rmdir /s /q ".temp" 2> nul
        mkdir ".temp"

        echo enabling 'bcdedit testsigning'
        bcdedit /set {default} testsigning on

        echo downloading 'crosec.zip'
        @echo on
        curl -s -o ".temp\crosec.zip" -L "https://github.com/DHowett/FrameworkWindowsUtils/releases/download/v0.0.2/CrosEC-0.0.2-4ac038b.zip" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo failed to download 'crosec.zip'
           exit /b 1
        )

        echo extracting 'crosec.zip'
        @echo on
        tar -xf ".temp\crosec.zip" --strip-components=1 -C ".temp" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo failed to extract 'crosec.zip'
           exit /b 2
        )

        echo installing 'crosec' driver

        cd /d ".temp"
        @echo on
        ".\installer" install
        @echo off
        if %errorLevel% neq 0 (
            cd /d "%~dp0"
            echo failed to run the 'crosec' driver installation
            exit /b 3
        )
        cd /d "%~dp0"

        echo testing 'crosec' driver
        @echo on
        ".temp\fauxectool" > ".temp\test-result.txt"
        @echo off

        set count=0
        for %%i in (".temp\test-result.txt") do @set count=%%~zi
        if "%count%" == "0" (
           echo 'crosec' driver not installed correctly
           exit /b 4
        )

        rmdir /s /q "%ProgramFiles%\crosec" 2> nul
        echo copying '.temp' to '%ProgramFiles%\crosec'
        @echo on
        xcopy /e /i ".temp" "%ProgramFiles%\crosec" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo unable to copy '.temp' to '%ProgramFiles%\ectool'
           exit /b 5
        )

        GOTO :EOF

    :install-ectool
        echo setting up 'ectool'
        rmdir /s /q ".temp" 2> nul
        mkdir ".temp"

        echo downloading 'artifact.zip'
        @echo on
        curl -s -o ".temp\artifact.zip" -L "https://gitlab.howett.net/DHowett/ectool/-/jobs/904/artifacts/download?file_type=archive" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo failed to download 'artifact.zip'
           exit /b 1
        )

        echo extracting 'artifact.zip'
        @echo on
        tar -xf ".temp\artifact.zip" --strip-components=3 -C ".temp" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo failed to extract 'artifact.zip'
           exit /b 2
        )

        rmdir /s /q "%ProgramFiles%\ectool" 2> nul
        echo creating directory '%ProgramFiles%\ectool'
        @echo on
        mkdir "%ProgramFiles%\ectool" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo unable to create directory '%ProgramFiles%\ectool'
           exit /b 3
        )

        @echo %PATH% | findstr /I /C:"%ProgramFiles%\ectool" >nul
        if %errorLevel% neq 0 (
            set "addedEnvironmentPaths=%addedEnvironmentPaths%;%ProgramFiles%\ectool"
        )

        echo installing 'ectool.exe' to '%ProgramFiles%\ectool'
        @echo on
        copy /v ".temp\ectool.exe" "%ProgramFiles%\ectool" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo unable to install 'ectool.exe'
           exit /b 3
        )

        GOTO :EOF

    :install-nssm
        echo setting up 'nssm'
        rmdir /s /q ".temp" 2> nul
        mkdir ".temp"

        echo downloading 'nssm.zip'
        @echo on
        curl -s -o ".temp\nssm.zip" -L "https://nssm.cc/release/nssm-2.24.zip" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo failed to download 'nssm.zip'
           exit /b 1
        )

        echo extracting 'nssm.zip'
        @echo on
        tar -xf ".temp\nssm.zip" --strip-components=1 -C ".temp" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo failed to extract 'nssm.zip'
           exit /b 2
        )

        echo creating directory '%ProgramFiles%\nssm'
        @echo on
        mkdir "%ProgramFiles%\nssm" > nul 2> nul
        @echo off

        echo installing 'nssm.exe' to '%ProgramFiles%\nssm\'
        @echo on
        copy /v ".temp\win64\nssm.exe" "%ProgramFiles%\nssm\" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo unable to install 'nssm.exe'
           exit /b 3
        )

        GOTO :EOF


    :install-fw-fanctrl
        echo setting up 'fw-fanctrl'
        rmdir /s /q "%ProgramFiles%\fw-fanctrl" 2> nul
        echo creating directory '%ProgramFiles%\fw-fanctrl'
        @echo on
        mkdir "%ProgramFiles%\fw-fanctrl" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo unable to create directory '%ProgramFiles%\fw-fanctrl'
           exit /b 3
        )

        @echo %PATH% | findstr /I /C:"%ProgramFiles%\fw-fanctrl" >nul
        if %errorLevel% neq 0 (
            set "addedEnvironmentPaths=%addedEnvironmentPaths%;%ProgramFiles%\fw-fanctrl"
        )

        echo installing 'fanctrl.py' to '%ProgramFiles%\fw-fanctrl'
        @echo on
        copy /v ".\fanctrl.py" "%ProgramFiles%\fw-fanctrl" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo unable to install 'fanctrl.py'
           exit /b 3
        )

        echo installing '.\services\windows\run-service.bat' to '%ProgramFiles%\fw-fanctrl'
        @echo on
        copy /v ".\services\windows\run-service.bat" "%ProgramFiles%\fw-fanctrl" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo unable to install '.\services\windows\run-service.bat'
           exit /b 4
        )

        echo installing '.\services\windows\run-service.bat' to '%ProgramFiles%\fw-fanctrl'
        @echo on
        copy /v ".\services\windows\run-service.bat" "%ProgramFiles%\fw-fanctrl" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo unable to install '.\services\windows\run-service.bat'
           exit /b 4
        )

        powershell -Command "(gc '%ProgramFiles%\fw-fanctrl\run-service.bat') -replace '####CONFIG_PATH####', '%Appdata%\fw-fanctrl\config.json' | Out-File -encoding ASCII '%ProgramFiles%\fw-fanctrl\run-service.bat'"

        echo installing '.\services\windows\fw-fanctrl.bat' to '%ProgramFiles%\fw-fanctrl'
        @echo on
        copy /v ".\services\windows\fw-fanctrl.bat" "%ProgramFiles%\fw-fanctrl" > nul
        @echo off
        if %errorLevel% neq 0 (
           echo unable to install '.\services\windows\fw-fanctrl.bat'
           exit /b 4
        )

        powershell -Command "(gc '%ProgramFiles%\fw-fanctrl\fw-fanctrl.bat') -replace '####PYTHON_PATH####', '%localAppData%\Programs\Python\Python312\python' | Out-File -encoding ASCII '%ProgramFiles%\fw-fanctrl\fw-fanctrl.bat'"

        echo creating directory '%Appdata%\fw-fanctrl'
        if not exist "%Appdata%\fw-fanctrl" mkdir "%Appdata%\fw-fanctrl"

        echo installing 'config.json' in '%Appdata%\fw-fanctrl\config.json'
        if not exist "%Appdata%\fw-fanctrl\config.json" echo n | copy /-y ".\config.json" "%Appdata%\fw-fanctrl\config.json" > nul

        echo creating 'fw-fanctrl' service
        @echo on
        "%ProgramFiles%\nssm\nssm" install "fw-fanctrl" "%ProgramFiles%\fw-fanctrl\run-service.bat"
        "%ProgramFiles%\nssm\nssm" set "fw-fanctrl" Start "SERVICE_DELAYED_AUTO_START"
        "%ProgramFiles%\nssm\nssm" set "fw-fanctrl" DisplayName "Framework Fanctrl"
        "%ProgramFiles%\nssm\nssm" set "fw-fanctrl" Description "A simple systemd service to better control Framework Laptop's fan(s)"
        "%ProgramFiles%\nssm\nssm" set "fw-fanctrl" AppStdout "%ProgramFiles%\fw-fanctrl\out.log"
        "%ProgramFiles%\nssm\nssm" set "fw-fanctrl" AppStderr "%ProgramFiles%\fw-fanctrl\out.log"
        @echo off

        GOTO :EOF
    GOTO :EOF

:UNINSTALL
    echo uninstalling

    CALL :uninstall-fw-fanctrl

    CALL :uninstall-nssm

    CALL :uninstall-ectool

    CALL :uninstall-crosec

    rmdir /s /q ".temp" 2> nul

    pause

    GOTO :EOF

    :uninstall-fw-fanctrl
        echo removing 'fw-fanctrl'

        echo stopping 'fw-fanctrl' service
        @echo on
        "%ProgramFiles%\nssm\nssm" stop "fw-fanctrl"
        @echo off

        echo removing 'fw-fanctrl' service
        @echo on
        "%ProgramFiles%\nssm\nssm" remove "fw-fanctrl" confirm
        @echo off

        echo removing directory '%ProgramFiles%\fw-fanctrl'
        rmdir /s /q "%ProgramFiles%\fw-fanctrl" 2> nul

        GOTO :EOF

    :uninstall-nssm
        echo removing 'nssm'

        echo removing directory '%ProgramFiles%\nssm'
        rmdir /s /q "%ProgramFiles%\nssm" 2> nul

    :uninstall-ectool
        echo removing 'ectool'

        echo setting the fan control back to normal
        @echo on
        "%ProgramFiles%\ectool\ectool" autofanctrl
        @echo off

        echo removing directory '%ProgramFiles%\ectool'
        rmdir /s /q "%ProgramFiles%\ectool" 2> nul

        GOTO :EOF

    :uninstall-crosec
        echo removing 'crosec'
        
        echo uninstalling 'crosec' driver
        @echo on
        "%ProgramFiles%\crosec\installer" uninstall
        @echo off

        echo removing directory '%ProgramFiles%\crosec'
        rmdir /s /q "%ProgramFiles%\crosec" 2> nul

        echo disabling 'bcdedit testsigning'
        bcdedit /set {default} testsigning off

        GOTO :EOF
    GOTO :EOF


:ARG-PARSER
    :: Loop until two consecutive empty args
    :loopargs
        IF "%~1%~2" EQU "" GOTO :EOF

        set "arg1=%~1" 
        set "arg2=%~2"
        shift

        :: Allow either / or -
        set "tst1=%arg1:-=/%"
        if "%arg1%" NEQ "" (
            set "tst1=%tst1:~0,1%"
        ) ELSE (
            set "tst1="
        )

        set "tst2=%arg2:-=/%"
        if "%arg2%" NEQ "" (
            set "tst2=%tst2:~0,1%"
        ) ELSE (
            set "tst2="
        )


        :: Capture assignments (eg. /foo bar)
        IF "%tst1%" EQU "/"  IF "%tst2%" NEQ "/" IF "%tst2%" NEQ "" (
            set "ARG_%arg1:~1%=%arg2%"
            GOTO loopargs
        )

        :: Capture flags (eg. /foo)
        IF "%tst1%" EQU "/" (
            set "ARG_%arg1:~1%=1"
            GOTO loopargs
        )
    GOTO loopargs
    GOTO :EOF

