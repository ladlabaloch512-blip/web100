import sys

# Required Library for image processing: pip install Pillow
try:
    from PIL import Image, ImageTk
except ImportError:
    print("[ERROR] Missing required library: Pillow. Please open CMD and run: pip install Pillow")
    sys.exit(1)

# Required Library for browser automation
try:
    import undetected_chromedriver as uc
    import undetected_chromedriver.patcher as uc_patcher
except ImportError:
    print("[ERROR] Missing required library: undetected-chromedriver. Please open CMD and run: pip install undetected-chromedriver")
    sys.exit(1)

# Required Library for system monitoring
try:
    import psutil
except ImportError:
    print("[ERROR] Missing required library: psutil. Please open CMD and run: pip install psutil")
    sys.exit(1)

# Required Library for HTTP requests
try:
    import requests
except ImportError:
    print("[ERROR] Missing required library: requests. Please open CMD and run: pip install requests")
    sys.exit(1)

from src.ui.dashboard import ControlPanel
from src.licensing import verify_license, show_activation_screen

if __name__ == "__main__":
    is_valid, msg = verify_license()
    if not is_valid:
        show_activation_screen(msg)
        is_valid, _ = verify_license()
        if not is_valid:
            sys.exit(0)

    app = ControlPanel()
    app.root.mainloop()
