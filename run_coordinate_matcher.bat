@echo off
REM Run coordinate matching test with specified parameters
REM Usage: run_coordinate_matcher.bat [overview_path] [session_image_paths...] [--rotation 1|-1] [--show]

REM Default values
set OVERVIEW=sample_data\overview.tif
set ROTATION=1
set SHOW=

REM Check for overview parameter
if not "%~1"=="" (
    set OVERVIEW=%~1
    shift
)

REM Initialize sessions list
set SESSIONS=

REM Parse arguments
:parse_args
if "%~1"=="" goto run_script

if "%~1"=="--rotation" (
    set ROTATION=%~2
    shift
    shift
    goto parse_args
)

if "%~1"=="--show" (
    set SHOW=--show
    shift
    goto parse_args
)

REM If not a flag, assume it's a session image path
set SESSIONS=%SESSIONS% "%~1"
shift
goto parse_args

:run_script
echo Running coordinate matcher with:
echo   Overview: %OVERVIEW%
echo   Sessions: %SESSIONS%
echo   Rotation Direction: %ROTATION% (%if %ROTATION%==1 (echo CCW) else (echo CW)%)
echo   Show Results: %if "%SHOW%"=="" (echo No) else (echo Yes)%

REM Run the Python script
python coordinate_matching_test.py --overview %OVERVIEW% --sessions %SESSIONS% --rotation %ROTATION% %SHOW%

pause
