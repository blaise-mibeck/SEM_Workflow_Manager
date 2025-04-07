@echo off
echo Building SEM_Workflow_Manager executable...

echo Current directory: %CD%

:: Clean up previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: Run PyInstaller with verbose output
pyinstaller --onefile --windowed --name "SEM_Workflow_Manager" ^
  --add-data "config.json;." ^
  --log-level DEBUG ^
  main.py

:: Check if build was successful
if exist dist\SEM_Workflow_Manager.exe (
  echo Build successful! Executable created at:
  echo %CD%\dist\SEM_Workflow_Manager.exe
) else (
  echo Build failed. Please check the output above for errors.
)

pause
