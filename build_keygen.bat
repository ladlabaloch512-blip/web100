@echo off
echo Installing required Python packages...
pip install pyinstaller

echo.
echo Building Abiz Global Admin Keygen Executable...
python -m PyInstaller --noconfirm --onefile --noconsole --windowed --add-data "src;src/"  "admin_keygen.py"

echo.
echo Build complete. The standalone executable is located in the "dist" folder.
pause
