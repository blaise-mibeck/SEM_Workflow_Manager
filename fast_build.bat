@echo off
echo Building fast-startup SEM_Workflow_Manager...

echo Current directory: %CD%

:: Clean up previous builds
if exist build_fast rmdir /s /q build_fast
if exist dist_fast rmdir /s /q dist_fast

:: Run PyInstaller without --onefile for faster startup
pyinstaller --workpath=build_fast --distpath=dist_fast --name "SEM_Workflow_Manager" ^
  --add-data "config.json;." ^
  --noconfirm ^
  --windowed ^
  main.py

:: Check if build was successful
if exist dist_fast\SEM_Workflow_Manager\SEM_Workflow_Manager.exe (
  echo Build successful! Executable created in folder:
  echo %CD%\dist_fast\SEM_Workflow_Manager
) else (
  echo Build failed. Please check the output above for errors.
)

pause
