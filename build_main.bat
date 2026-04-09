@echo off
echo Installing required Python packages...
pip install Pillow undetected-chromedriver psutil requests pyinstaller

echo.
echo Building Abiz Global Enterprise Main Executable...
pyinstaller --noconfirm --onedir --windowed --add-data "src;src/"  "main.py"

echo.
echo Build complete. The executable is located in the "dist\main" folder.
pause
