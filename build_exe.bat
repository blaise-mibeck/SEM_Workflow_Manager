@echo off
echo Building SEM_Workflow_Manager executable...

:: Check if resources directory exists
if exist resources (
  echo Resources directory found, using icon...
  pyinstaller --noconfirm --onefile --windowed --icon=resources/app_icon.ico --add-data "config.json;." --name "SEM_Workflow_Manager" main.py
) else (
  echo Resources directory not found, building without icon...
  pyinstaller --noconfirm --onefile --windowed --add-data "config.json;." --name "SEM_Workflow_Manager" main.py
)

:: Check if build was successful
if exist dist\SEM_Workflow_Manager.exe (
  echo Build successful! Executable created at dist\SEM_Workflow_Manager.exe
) else (
  echo Build may have failed. Please check the output above for errors.
)

echo Done!
pause
