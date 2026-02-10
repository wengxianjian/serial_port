@echo off
echo Packaging Serial Port Tool...

REM Clean previous build files
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "serial_tool.spec" del "serial_tool.spec"

REM Use PyInstaller to package
pyinstaller ^
    --name="SerialTool" ^
    --onefile ^
    --windowed ^
    --icon=serial_port.ico ^
    --add-data="serial_port.ico;." ^
    --clean ^
    --noconsole ^
    Serial_Port_Tool.py

echo.
echo Packaging complete!
echo Executable file: dist\SerialTool.exe
pause