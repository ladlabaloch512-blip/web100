@echo off
echo Installing required Python packages...
pip install Pillow undetected-chromedriver psutil requests tkcalendar pyinstaller

echo.
echo Building Abiz Global Enterprise Main Executable...
python -m PyInstaller --noconfirm --onefile --noconsole --windowed --add-data "src;src/"  "main.py"

echo.
echo Build complete. The standalone executable is located in the "dist" folder.
pause
