@echo off
echo Packaging Serial Port...

REM Clean previous build files
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "serial_port.spec" del "serial_port.spec"

REM Use PyInstaller to package
pyinstaller ^
    --name="serial_port" ^
    --onefile ^
    --windowed ^
    --icon=serial_port.ico ^
    --add-data="serial_port.ico;." ^
    --clean ^
    --noconsole ^
    serial_port.py

echo.
echo Packaging complete!
echo Executable file: dist\Serial_port.exe
pause