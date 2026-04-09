@echo off
echo Installing required Python packages...
pip install Pillow undetected-chromedriver psutil requests pyinstaller

echo.
echo Building Abiz Global Enterprise Main Executable...
pyinstaller --noconfirm --onefile --noconsole --windowed --add-data "src;src/"  "main.py"

echo.
echo Build complete. The standalone executable is located in the "dist" folder.
pause
