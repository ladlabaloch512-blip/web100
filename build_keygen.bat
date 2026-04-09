@echo off
echo Installing required Python packages...
pip install pyinstaller

echo.
echo Building Abiz Global Admin Keygen Executable...
pyinstaller --noconfirm --onedir --windowed --add-data "src;src/"  "admin_keygen.py"

echo.
echo Build complete. The executable is located in the "dist\admin_keygen" folder.
pause
