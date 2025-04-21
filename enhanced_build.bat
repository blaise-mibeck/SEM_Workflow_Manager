@echo off
echo Building SEM_Workflow_Manager executable...

:: Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo Python is not installed or not in PATH. Please install Python.
  goto :error
)

:: Check if virtual environment exists, create if not
if not exist venv (
  echo Virtual environment not found. Creating new virtual environment...
  python -m venv venv
  if %ERRORLEVEL% neq 0 (
    echo Failed to create virtual environment.
    goto :error
  )
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
  echo Failed to activate virtual environment.
  goto :error
)

:: Install required packages
echo Installing required packages...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
  echo Failed to install required packages.
  goto :error
)

:: Check for PyInstaller
where pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo PyInstaller not found. Installing...
  pip install pyinstaller
  if %ERRORLEVEL% neq 0 (
    echo Failed to install PyInstaller.
    goto :error
  )
)

:: Clean up previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

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
  echo Build successful! Executable created at:
  echo %CD%\dist\SEM_Workflow_Manager.exe
  goto :success
) else (
  echo Build failed. Please check the output above for errors.
  goto :error
)

:error
echo Build process encountered an error.
goto :end

:success
echo Build completed successfully!

:end
:: Deactivate virtual environment if activated
where deactivate >nul 2>&1
if %ERRORLEVEL% equ 0 (
  call deactivate
)

echo Done!
pause
