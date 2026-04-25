"""
DualSense PC Controller Manager
================================
Professional companion app that:
1. Reads DualSense input via HID (pydualsense)
2. Creates a virtual Xbox 360 controller via ViGEmBus (vgamepad)
3. Shows PlayStation buttons (✕, ○, △, □) — NOT Xbox!

Requirements:
- ViGEmBus driver installed (https://github.com/nathalie-sigmund/ViGEmBus/releases)
- pip install -r requirements.txt
"""

import ctypes
import os
import sys

# Ensure we can import from project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import DualSenseGUI

SINGLE_INSTANCE_MUTEX = "Local\\DualSenseControllerManagerSingleton"


def _acquire_single_instance_mutex():
    """Prevent launching multiple app copies that would create duplicate virtual pads."""
    if os.name != "nt":
        return None

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    mutex = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
    already_exists = kernel32.GetLastError() == 183
    if already_exists:
        if mutex:
            kernel32.CloseHandle(mutex)
        user32.MessageBoxW(
            None,
            "Uygulama zaten acik. Birden fazla kopya acilmasi sanal kollarin çakışmasına neden olur.",
            "Universal Gamepad Manager",
            0x30,
        )
        return None

    return mutex


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    if not is_admin():
        # Re-run the program with admin rights
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit(0)


def main():
    run_as_admin()  # Ensure we have admin rights for driver/vibration
    mutex = _acquire_single_instance_mutex()
    if os.name == "nt" and mutex is None:
        return

    try:
        app = DualSenseGUI()
        app.mainloop()
    finally:
        if mutex:
            ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
