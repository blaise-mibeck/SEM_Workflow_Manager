@echo off
REM Run template matching test with example files
REM Usage: run_template_test.bat [overview_image] [session_image] [rotation_angle] [rotation_direction]

set OVERVIEW=%1
set TEMPLATE=%2
set ROTATION=%3
set DIRECTION=%4

REM Default values if not provided
if "%OVERVIEW%"=="" (
    echo Overview image not specified. Please use: run_template_test.bat overview_image session_image [rotation_angle] [rotation_direction]
    echo Example: run_template_test.bat samples\overview.tif samples\session.tif 30 -1
    exit /b 1
)

if "%TEMPLATE%"=="" (
    echo Session image not specified. Please use: run_template_test.bat overview_image session_image [rotation_angle] [rotation_direction]
    echo Example: run_template_test.bat samples\overview.tif samples\session.tif 30 -1
    exit /b 1
)

if "%ROTATION%"=="" (
    set ROTATION=0
)

if "%DIRECTION%"=="" (
    set DIRECTION=1
)

echo Running template matching test:
echo   Overview: %OVERVIEW%
echo   Template: %TEMPLATE%
echo   Rotation angle: %ROTATION% degrees
echo   Rotation direction: %if %DIRECTION%==1 (echo CCW) else (echo CW)%

python test_template_match.py --overview "%OVERVIEW%" --template "%TEMPLATE%" --rotation %ROTATION% --direction %DIRECTION%

echo.
echo Test complete
pause
